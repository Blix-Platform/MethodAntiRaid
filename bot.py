import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from datetime import datetime, timedelta
from database import Database

# Инициализация бота
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)
db = Database()

# Константы
EMBED_COLOR = 0x1E90FF  # Яркий синий цвет для современного вида
SECONDARY_COLOR = 0x2F3136  # Темный фон для акцентов

# Эмодзи для сообщений
EMOJI = {
    "shield": "🛡️",
    "settings": "⚙️",
    "warning": "⚠️",
    "success": "✅",
    "error": "❌",
    "info": "ℹ️",
    "lock": "🔒",
    "unlock": "🔓",
    "limit": "📊",
    "trusted": "👥",
    "add": "➕",
    "remove": "➖",
    "list": "📜",
    "back": "⬅️",
    "confirm": "✔️",
    "cancel": "✖️",
    "roles": "🎭",
    "channels": "📣",
    "alert": "🚨",
    "time": "🕒",
    "server": "🏰",
    "user": "👤",
    "help": "❓",
    "image": "🖼️"
}

# Класс для кнопок настроек
class SettingsView(discord.ui.View):
    def __init__(self, guild_id, owner_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.owner_id = owner_id
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            embed = discord.Embed(
                title=f"{EMOJI['error']} Ошибка доступа",
                description=f"Только владелец сервера может управлять настройками!",
                color=SECONDARY_COLOR,
                timestamp=datetime.now()
            )
            embed.set_footer(text="Anti Raid Bot • Ограниченный доступ")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Вкл/Выкл защиту", emoji="🛡️", style=discord.ButtonStyle.primary)
    async def toggle_protection(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_status = db.get_protection_status(self.guild_id)
        new_status = not current_status
        db.set_protection_status(self.guild_id, new_status)
        
        status_emoji = EMOJI['lock'] if new_status else EMOJI['unlock']
        status_text = "АКТИВНА" if new_status else "ОТКЛЮЧЕНА"
        
        embed = discord.Embed(
            title=f"{EMOJI['shield']} Статус защиты",
            description=f"**{status_emoji} Защита от рейдов {status_text}**",
            color=EMBED_COLOR,
            timestamp=datetime.now()
        )
        
        limits = db.get_action_limits(self.guild_id)
        embed.add_field(
            name=f"{EMOJI['limit']} Ограничения",
            value=(
                f"**{EMOJI['roles']} Роли:** {limits['role_limit']} действий/24ч\n"
                f"**{EMOJI['channels']} Каналы:** {limits['channel_limit']} действий/24ч"
            ),
            inline=False
        )
        
        trusted_count = len(db.get_trusted_users(self.guild_id))
        embed.add_field(
            name=f"{EMOJI['trusted']} Доверенные лица",
            value=f"Всего: **{trusted_count}** пользователей",
            inline=False
        )
        
        embed.set_footer(text="Anti Raid Bot • Настройки")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Настроить лимиты", emoji="📊", style=discord.ButtonStyle.primary)
    async def configure_limits(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = LimitSettingsModal(self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Доверенные лица", emoji="👥", style=discord.ButtonStyle.primary)
    async def manage_trusted_users(self, interaction: discord.Interaction, button: discord.ui.Button):
        trusted_view = TrustedUsersView(self.guild_id, self.owner_id)
        embed = discord.Embed(
            title=f"{EMOJI['trusted']} Управление доверенными лицами",
            description=(
                f"Управляйте списком доверенных пользователей.\n\n"
                f"{EMOJI['warning']} **ВНИМАНИЕ!**\n"
                f"Доверенные лица обходят защиту от рейдов.\n"
                f"Добавляйте только полностью проверенных пользователей!"
            ),
            color=EMBED_COLOR,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Anti Raid Bot • Управление")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
        await interaction.response.edit_message(embed=embed, view=trusted_view)

# Модальное окно для настройки лимитов
class LimitSettingsModal(discord.ui.Modal, title="Настройка лимитов"):
    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id
        
        limits = db.get_action_limits(guild_id)
        
        self.role_limit = discord.ui.TextInput(
            label="Лимит ролей (за 24 часа)",
            placeholder="Максимум действий с ролями",
            default=str(limits["role_limit"]),
            required=True
        )
        self.channel_limit = discord.ui.TextInput(
            label="Лимит каналов (за 24 часа)",
            placeholder="Максимум действий с каналами",
            default=str(limits["channel_limit"]),
            required=True
        )
        
        self.add_item(self.role_limit)
        self.add_item(self.channel_limit)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_limit = int(self.role_limit.value)
            channel_limit = int(self.channel_limit.value)
            
            if role_limit < 1 or channel_limit < 1:
                embed = discord.Embed(
                    title=f"{EMOJI['error']} Ошибка ввода",
                    description="Лимиты должны быть больше 0!",
                    color=SECONDARY_COLOR,
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Anti Raid Bot • Ошибка")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            db.set_action_limits(self.guild_id, role_limit, channel_limit)
            
            embed = discord.Embed(
                title=f"{EMOJI['success']} Лимиты обновлены",
                description=(
                    f"**{EMOJI['roles']} Роли:** {role_limit} действий/24ч\n"
                    f"**{EMOJI['channels']} Каналы:** {channel_limit} действий/24ч"
                ),
                color=EMBED_COLOR,
                timestamp=datetime.now()
            )
            embed.set_footer(text="Anti Raid Bot • Успех")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            embed = discord.Embed(
                title=f"{EMOJI['error']} Ошибка ввода",
                description="Введите корректные числа для лимитов!",
                color=SECONDARY_COLOR,
                timestamp=datetime.now()
            )
            embed.set_footer(text="Anti Raid Bot • Ошибка")
            await interaction.response.send_message(embed=embed, ephemeral=True)

# Класс для управления доверенными лицами
class TrustedUsersView(discord.ui.View):
    def __init__(self, guild_id, owner_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.owner_id = owner_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            embed = discord.Embed(
                title=f"{EMOJI['error']} Ошибка доступа",
                description="Только владелец может управлять доверенными лицами!",
                color=SECONDARY_COLOR,
                timestamp=datetime.now()
            )
            embed.set_footer(text="Anti Raid Bot • Ограниченный доступ")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Добавить", emoji="➕", style=discord.ButtonStyle.success)
    async def add_trusted_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"{EMOJI['add']} Добавление доверенного лица",
            description="Упомяните пользователя (@username) для добавления.",
            color=EMBED_COLOR,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Anti Raid Bot • Введите @username")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and len(m.mentions) > 0
        
        try:
            message = await bot.wait_for('message', check=check, timeout=60.0)
            
            try:
                await message.delete()
            except:
                pass
            
            mentioned_user = message.mentions[0]
            
            if db.is_trusted_user(self.guild_id, mentioned_user.id):
                embed = discord.Embed(
                    title=f"{EMOJI['info']} Уже добавлен",
                    description=f"{mentioned_user.mention} уже в списке доверенных!",
                    color=EMBED_COLOR,
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Anti Raid Bot • Информация")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"{EMOJI['warning']} Подтверждение добавления",
                description=(
                    f"Вы добавляете {mentioned_user.mention} в доверенные лица.\n\n"
                    f"**{EMOJI['warning']} ВНИМАНИЕ!**\n"
                    f"Это позволит пользователю обойти защиту от рейдов.\n"
                    f"Подтвердите действие:"
                ),
                color=0xFF4500,  # Оранжевый для предупреждения
                timestamp=datetime.now()
            )
            embed.set_footer(text="Anti Raid Bot • Подтверждение")
            
            confirm_view = ConfirmAddTrustedUserView(self.guild_id, mentioned_user.id, mentioned_user.mention)
            await interaction.followup.send(embed=embed, view=confirm_view, ephemeral=True)
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title=f"{EMOJI['error']} Время истекло",
                description="Вы не указали пользователя в течение 60 секунд.",
                color=SECONDARY_COLOR,
                timestamp=datetime.now()
            )
            embed.set_footer(text="Anti Raid Bot • Ошибка")
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Удалить", emoji="➖", style=discord.ButtonStyle.danger)
    async def remove_trusted_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        trusted_users = db.get_trusted_users(self.guild_id)
        
        if not trusted_users:
            embed = discord.Embed(
                title=f"{EMOJI['info']} Список пуст",
                description="Нет доверенных лиц для удаления.",
                color=EMBED_COLOR,
                timestamp=datetime.now()
            )
            embed.set_footer(text="Anti Raid Bot • Информация")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        select_view = RemoveTrustedUserView(self.guild_id, interaction.guild)
        
        embed = discord.Embed(
            title=f"{EMOJI['remove']} Удаление доверенного лица",
            description="Выберите пользователя для удаления:",
            color=EMBED_COLOR,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Anti Raid Bot • Выбор")
        await interaction.response.send_message(embed=embed, view=select_view, ephemeral=True)
    
    @discord.ui.button(label="Список", emoji="📜", style=discord.ButtonStyle.secondary)
    async def view_trusted_users(self, interaction: discord.Interaction, button: discord.ui.Button):
        trusted_users = db.get_trusted_users(self.guild_id)
        
        if not trusted_users:
            embed = discord.Embed(
                title=f"{EMOJI['trusted']} Доверенные лица",
                description="Список доверенных лиц пуст.",
                color=EMBED_COLOR,
                timestamp=datetime.now()
            )
            embed.set_footer(text="Anti Raid Bot • Список")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        guild = interaction.guild
        description = f"**Список доверенных лиц:**\n\n"
        
        for user_id in trusted_users:
            member = guild.get_member(user_id)
            if member:
                description += f"{EMOJI['user']} {member.mention} ({member.name})\n"
            else:
                description += f"{EMOJI['user']} ID: {user_id} (не найден)\n"
        
        embed = discord.Embed(
            title=f"{EMOJI['trusted']} Доверенные лица",
            description=description,
            color=EMBED_COLOR,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Anti Raid Bot • Список")
        embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Назад", emoji="⬅️", style=discord.ButtonStyle.primary)
    async def back_to_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings_view = SettingsView(self.guild_id, self.owner_id)
        
        protection_status = db.get_protection_status(self.guild_id)
        limits = db.get_action_limits(self.guild_id)
        trusted_count = len(db.get_trusted_users(self.guild_id))
        
        status_emoji = EMOJI['lock'] if protection_status else EMOJI['unlock']
        status_text = "АКТИВНА" if protection_status else "ОТКЛЮЧЕНА"
        
        embed = discord.Embed(
            title=f"{EMOJI['settings']} Настройки защиты",
            description="Выберите параметр для изменения:",
            color=EMBED_COLOR,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name=f"{EMOJI['shield']} Статус",
            value=f"**{status_emoji} Защита {status_text}**",
            inline=False
        )
        
        embed.add_field(
            name=f"{EMOJI['limit']} Лимиты",
            value=(
                f"**{EMOJI['roles']} Роли:** {limits['role_limit']} действий/24ч\n"
                f"**{EMOJI['channels']} Каналы:** {limits['channel_limit']} действий/24ч"
            ),
            inline=False
        )
        
        embed.add_field(
            name=f"{EMOJI['trusted']} Доверенные",
            value=f"Всего: **{trusted_count}** пользователей",
            inline=False
        )
        
        embed.set_footer(text="Anti Raid Bot • Настройки")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
        
        await interaction.response.edit_message(embed=embed, view=settings_view)

# Класс для подтверждения добавления
class ConfirmAddTrustedUserView(discord.ui.View):
    def __init__(self, guild_id, user_id, user_mention):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id
        self.user_mention = user_mention
    
    @discord.ui.button(label="Подтвердить", emoji="✔️", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        success = db.add_trusted_user(self.guild_id, self.user_id)
        
        if success:
            embed = discord.Embed(
                title=f"{EMOJI['success']} Успешно добавлено",
                description=f"{self.user_mention} добавлен в доверенные лица.",
                color=EMBED_COLOR,
                timestamp=datetime.now()
            )
        else:
            embed = discord.Embed(
                title=f"{EMOJI['error']} Ошибка",
                description=f"Не удалось добавить {self.user_mention}.",
                color=SECONDARY_COLOR,
                timestamp=datetime.now()
            )
        
        embed.set_footer(text="Anti Raid Bot • Результат")
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Отмена", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"{EMOJI['info']} Операция отменена",
            description="Добавление доверенного лица отменено.",
            color=EMBED_COLOR,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Anti Raid Bot • Отмена")
        await interaction.response.edit_message(embed=embed, view=None)

# Класс для выбора удаления
class RemoveTrustedUserView(discord.ui.View):
    def __init__(self, guild_id, guild):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.guild = guild
        
        trusted_users = db.get_trusted_users(guild_id)
        
        self.select = discord.ui.Select(
            placeholder="Выберите пользователя",
            min_values=1,
            max_values=1,
            options=[]
        )
        
        for user_id in trusted_users:
            member = guild.get_member(user_id)
            if member:
                self.select.add_option(
                    label=member.name,
                    value=str(user_id),
                    description=f"ID: {user_id}",
                    emoji="👤"
                )
            else:
                self.select.add_option(
                    label=f"Пользователь (ID: {user_id})",
                    value=str(user_id),
                    description="Не найден на сервере",
                    emoji="👤"
                )
        
        self.select.callback = self.select_callback
        self.add_item(self.select)
    
    async def select_callback(self, interaction: discord.Interaction):
        user_id = int(self.select.values[0])
        
        success = db.remove_trusted_user(self.guild_id, user_id)
        
        if success:
            member = self.guild.get_member(user_id)
            user_mention = member.mention if member else f"ID: {user_id}"
            
            embed = discord.Embed(
                title=f"{EMOJI['success']} Успешно удалено",
                description=f"{user_mention} удален из доверенных лиц.",
                color=EMBED_COLOR,
                timestamp=datetime.now()
            )
        else:
            embed = discord.Embed(
                title=f"{EMOJI['error']} Ошибка",
                description="Не удалось удалить пользователя.",
                color=SECONDARY_COLOR,
                timestamp=datetime.now()
            )
        
        embed.set_footer(text="Anti Raid Bot • Результат")
        await interaction.response.edit_message(embed=embed, view=None)

@bot.event
async def on_ready():
    print(f'Бот {bot.user.name} успешно запущен!')
    try:
        synced = await bot.tree.sync()
        print(f'Синхронизировано {len(synced)} команд')
    except Exception as e:
        print(f'Ошибка синхронизации: {e}')

@bot.tree.command(name="help", description="Показать справку по командам")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"{EMOJI['shield']} Anti Raid Bot",
        description="Система защиты от рейдов и несанкционированных изменений",
        color=EMBED_COLOR,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name=f"{EMOJI['info']} Доступные команды",
        value=(
            f"**{EMOJI['help']} /help** - Показать справку\n"
            f"**{EMOJI['settings']} /settings** - Настроить защиту (владелец)\n"
            f"**{EMOJI['shield']} /status** - Текущий статус защиты\n"
            f"**{EMOJI['trusted']} /trusted** - Управление доверенными лицами"
        ),
        inline=False
    )
    
    embed.add_field(
        name=f"{EMOJI['shield']} Возможности",
        value=(
            f"**{EMOJI['roles']} Контроль ролей**\n"
            f"**{EMOJI['channels']} Контроль каналов**\n"
            f"**{EMOJI['alert']} Автоматическая защита**\n"
            f"**{EMOJI['warning']} Уведомления владельца**"
        ),
        inline=False
    )
    
    embed.add_field(
        name=f"{EMOJI['warning']} Важно",
        value=(
            f"Доверенные лица могут обходить защиту.\n"
            f"Добавляйте только проверенных пользователей!"
        ),
        inline=False
    )
    
    embed.set_footer(text="Anti Raid Bot • Справка")
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="settings", description="Настройки защиты от рейда")
async def settings_command(interaction: discord.Interaction):
    if interaction.guild.owner_id != interaction.user.id:
        embed = discord.Embed(
            title=f"{EMOJI['error']} Ошибка доступа",
            description="Только владелец сервера может использовать эту команду!",
            color=SECONDARY_COLOR,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Anti Raid Bot • Ограниченный доступ")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    protection_status = db.get_protection_status(interaction.guild.id)
    limits = db.get_action_limits(interaction.guild.id)
    trusted_count = len(db.get_trusted_users(interaction.guild.id))
    
    status_emoji = EMOJI['lock'] if protection_status else EMOJI['unlock']
    status_text = "АКТИВНА" if protection_status else "ОТКЛЮЧЕНА"
    
    view = SettingsView(interaction.guild.id, interaction.guild.owner_id)
    
    embed = discord.Embed(
        title=f"{EMOJI['settings']} Настройки защиты",
        description="Выберите параметр для настройки:",
        color=EMBED_COLOR,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name=f"{EMOJI['shield']} Статус",
        value=f"**{status_emoji} Защита {status_text}**",
        inline=False
    )
    
    embed.add_field(
        name=f"{EMOJI['limit']} Лимиты",
        value=(
            f"**{EMOJI['roles']} Роли:** {limits['role_limit']} действий/24ч\n"
            f"**{EMOJI['channels']} Каналы:** {limits['channel_limit']} действий/24ч"
        ),
        inline=False
    )
    
    embed.add_field(
        name=f"{EMOJI['trusted']} Доверенные",
        value=f"Всего: **{trusted_count}** пользователей",
        inline=False
    )
    
    embed.set_footer(text="Anti Raid Bot • Настройки")
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="status", description="Показать статус защиты")
async def status_command(interaction: discord.Interaction):
    protection_status = db.get_protection_status(interaction.guild.id)
    limits = db.get_action_limits(interaction.guild.id)
    
    status_emoji = EMOJI['lock'] if protection_status else EMOJI['unlock']
    status_text = "АКТИВНА" if protection_status else "ОТКЛЮЧЕНА"
    
    embed = discord.Embed(
        title=f"{EMOJI['shield']} Статус защиты",
        description=f"**{status_emoji} Защита от рейдов {status_text}**",
        color=EMBED_COLOR,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name=f"{EMOJI['limit']} Ограничения",
        value=(
            f"**{EMOJI['roles']} Роли:** {limits['role_limit']} действий/24ч\n"
            f"**{EMOJI['channels']} Каналы:** {limits['channel_limit']} действий/24ч"
        ),
        inline=False
    )
    
    owner = interaction.guild.owner
    embed.add_field(
        name=f"{EMOJI['user']} Владелец",
        value=f"{owner.mention} ({owner.name})",
        inline=False
    )
    
    embed.set_footer(text="Anti Raid Bot • Статус")
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="trusted", description="Управление доверенными лицами")
async def trusted_command(interaction: discord.Interaction):
    if interaction.guild.owner_id != interaction.user.id:
        embed = discord.Embed(
            title=f"{EMOJI['error']} Ошибка доступа",
            description="Только владелец может управлять доверенными лицами!",
            color=SECONDARY_COLOR,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Anti Raid Bot • Ограниченный доступ")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    trusted_view = TrustedUsersView(interaction.guild.id, interaction.guild.owner_id)
    
    embed = discord.Embed(
        title=f"{EMOJI['trusted']} Доверенные лица",
        description=(
            f"Управление списком доверенных пользователей.\n\n"
            f"**{EMOJI['warning']} ВНИМАНИЕ!**\n"
            f"Доверенные лица могут обходить защиту.\n"
            f"Добавляйте только проверенных пользователей!"
        ),
        color=EMBED_COLOR,
        timestamp=datetime.now()
    )
    
    embed.set_footer(text="Anti Raid Bot • Управление")
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    
    await interaction.response.send_message(embed=embed, view=trusted_view, ephemeral=True)

@bot.event
async def on_guild_role_create(role):
    guild = role.guild
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        user = entry.user
        
        if not db.get_protection_status(guild.id):
            return
        
        if user.id == guild.owner_id or db.is_trusted_user(guild.id, user.id):
            return
        
        db.log_action(guild.id, user.id, "role_create")
        
        limits = db.get_action_limits(guild.id)
        role_actions = db.count_user_actions(guild.id, user.id, "role_create") + db.count_user_actions(guild.id, user.id, "role_delete")
        
        if role_actions > limits["role_limit"]:
            try:
                await remove_all_roles(user, guild)
                await notify_owner(guild, user, "роли", role_actions, limits["role_limit"])
            except Exception as e:
                print(f"Ошибка при создании роли: {e}")

@bot.event
async def on_guild_role_delete(role):
    guild = role.guild
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        user = entry.user
        
        if not db.get_protection_status(guild.id):
            return
        
        if user.id == guild.owner_id or db.is_trusted_user(guild.id, user.id):
            return
        
        db.log_action(guild.id, user.id, "role_delete")
        
        limits = db.get_action_limits(guild.id)
        role_actions = db.count_user_actions(guild.id, user.id, "role_create") + db.count_user_actions(guild.id, user.id, "role_delete")
        
        if role_actions > limits["role_limit"]:
            try:
                await remove_all_roles(user, guild)
                await notify_owner(guild, user, "роли", role_actions, limits["role_limit"])
            except Exception as e:
                print(f"Ошибка при удалении роли: {e}")

@bot.event
async def on_guild_channel_create(channel):
    guild = channel.guild
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
        user = entry.user
        
        if not db.get_protection_status(guild.id):
            return
        
        if user.id == guild.owner_id or db.is_trusted_user(guild.id, user.id):
            return
        
        db.log_action(guild.id, user.id, "channel_create")
        
        limits = db.get_action_limits(guild.id)
        channel_actions = db.count_user_actions(guild.id, user.id, "channel_create") + db.count_user_actions(guild.id, user.id, "channel_delete")
        
        if channel_actions > limits["channel_limit"]:
            try:
                await remove_all_roles(user, guild)
                await notify_owner(guild, user, "каналы", channel_actions, limits["channel_limit"])
            except Exception as e:
                print(f"Ошибка при создании канала: {e}")

@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        user = entry.user
        
        if not db.get_protection_status(guild.id):
            return
        
        if user.id == guild.owner_id or db.is_trusted_user(guild.id, user.id):
            return
        
        db.log_action(guild.id, user.id, "channel_delete")
        
        limits = db.get_action_limits(guild.id)
        channel_actions = db.count_user_actions(guild.id, user.id, "channel_create") + db.count_user_actions(guild.id, user.id, "channel_delete")
        
        if channel_actions > limits["channel_limit"]:
            try:
                await remove_all_roles(user, guild)
                await notify_owner(guild, user, "каналы", channel_actions, limits["channel_limit"])
            except Exception as e:
                print(f"Ошибка при удалении канала: {e}")

async def remove_all_roles(user, guild):
    member = guild.get_member(user.id)
    if member:
        roles_to_keep = [role for role in member.roles if role.managed or role.is_default()]
        
        try:
            await member.edit(roles=roles_to_keep, reason="Anti Raid Bot: превышение лимита")
            print(f"Сняты роли с {member.name} на {guild.name}")
        except discord.Forbidden:
            print(f"Недостаточно прав для снятия ролей с {member.name} на {guild.name}")
        except Exception as e:
            print(f"Ошибка при снятии ролей: {e}")

async def notify_owner(guild, user, action_type, count, limit):
    owner = guild.owner
    
    if owner:
        embed = discord.Embed(
            title=f"{EMOJI['alert']} Обнаружен рейд!",
            description=f"**{user.mention} ({user.name})** превысил лимит действий!",
            color=0xFF4500,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name=f"{EMOJI['info']} Подробности",
            value=(
                f"**{EMOJI['roles'] if action_type == 'роли' else EMOJI['channels']} Тип:** {action_type}\n"
                f"**{EMOJI['limit']} Действий:** {count}\n"
                f"**{EMOJI['limit']} Лимит:** {limit}\n"
                f"**{EMOJI['server']} Сервер:** {guild.name}"
            ),
            inline=False
        )
        
        embed.add_field(
            name=f"{EMOJI['shield']} Действия",
            value="Все роли пользователя сняты.",
            inline=False
        )
        
        embed.set_footer(text="Anti Raid Bot • Уведомление")
        embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
        
        try:
            await owner.send(embed=embed)
        except discord.Forbidden:
            print(f"Невозможно отправить уведомление владельцу {guild.name}")
        except Exception as e:
            print(f"Ошибка уведомления: {e}")

def run_bot(token):
    bot.run(token)

# Запуск бота
bot.run("")