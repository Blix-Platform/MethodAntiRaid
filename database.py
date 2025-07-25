import sqlite3
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_path='database.db'):
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
        except sqlite3.Error as e:
            print(f"Ошибка подключения к базе данных: {e}")
    
    def create_tables(self):
        try:
            # Таблица для хранения состояния защиты (вкл/выкл)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS protection_status (
                guild_id INTEGER PRIMARY KEY,
                is_enabled INTEGER DEFAULT 0
            )
            ''')
            
            # Таблица для хранения лимитов действий
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_limits (
                guild_id INTEGER PRIMARY KEY,
                role_limit INTEGER DEFAULT 5,
                channel_limit INTEGER DEFAULT 5
            )
            ''')
            
            # Таблица для хранения доверенных лиц
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trusted_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, user_id)
            )
            ''')
            
            # Таблица для отслеживания действий пользователей
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                action_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Таблица для хранения изображений серверов
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_images (
                guild_id INTEGER PRIMARY KEY,
                image_url TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Ошибка создания таблиц: {e}")
    
    def close(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            self.connection.close()
    
    # Методы для работы с состоянием защиты
    def get_protection_status(self, guild_id):
        """Получение статуса защиты для сервера"""
        try:
            self.cursor.execute("SELECT is_enabled FROM protection_status WHERE guild_id = ?", (guild_id,))
            result = self.cursor.fetchone()
            if result:
                return bool(result[0])
            else:
                # Если записи нет, создаем со значением по умолчанию (выключено)
                self.cursor.execute("INSERT INTO protection_status (guild_id, is_enabled) VALUES (?, 0)", (guild_id,))
                self.connection.commit()
                return False
        except sqlite3.Error as e:
            print(f"Ошибка получения статуса защиты: {e}")
            return False
    
    def set_protection_status(self, guild_id, status):
        """Установка статуса защиты для сервера"""
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO protection_status (guild_id, is_enabled) VALUES (?, ?)",
                (guild_id, int(status))
            )
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка установки статуса защиты: {e}")
            return False
    
    # Методы для работы с лимитами действий
    def get_action_limits(self, guild_id):
        """Получение лимитов действий для сервера"""
        try:
            self.cursor.execute("SELECT role_limit, channel_limit FROM action_limits WHERE guild_id = ?", (guild_id,))
            result = self.cursor.fetchone()
            if result:
                return {"role_limit": result[0], "channel_limit": result[1]}
            else:
                # Если записи нет, создаем со значениями по умолчанию
                self.cursor.execute(
                    "INSERT INTO action_limits (guild_id, role_limit, channel_limit) VALUES (?, 5, 5)",
                    (guild_id,)
                )
                self.connection.commit()
                return {"role_limit": 5, "channel_limit": 5}
        except sqlite3.Error as e:
            print(f"Ошибка получения лимитов действий: {e}")
            return {"role_limit": 5, "channel_limit": 5}
    
    def set_action_limits(self, guild_id, role_limit, channel_limit):
        """Установка лимитов действий для сервера"""
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO action_limits (guild_id, role_limit, channel_limit) VALUES (?, ?, ?)",
                (guild_id, role_limit, channel_limit)
            )
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка установки лимитов действий: {e}")
            return False
    
    # Методы для работы с доверенными лицами
    def add_trusted_user(self, guild_id, user_id):
        """Добавление пользователя в список доверенных лиц"""
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO trusted_users (guild_id, user_id) VALUES (?, ?)",
                (guild_id, user_id)
            )
            self.connection.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Ошибка добавления доверенного лица: {e}")
            return False
    
    def remove_trusted_user(self, guild_id, user_id):
        """Удаление пользователя из списка доверенных лиц"""
        try:
            self.cursor.execute(
                "DELETE FROM trusted_users WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            )
            self.connection.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Ошибка удаления доверенного лица: {e}")
            return False
    
    def is_trusted_user(self, guild_id, user_id):
        """Проверка, является ли пользователь доверенным лицом"""
        try:
            self.cursor.execute(
                "SELECT 1 FROM trusted_users WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            )
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Ошибка проверки доверенного лица: {e}")
            return False
    
    def get_trusted_users(self, guild_id):
        """Получение списка доверенных лиц для сервера"""
        try:
            self.cursor.execute(
                "SELECT user_id FROM trusted_users WHERE guild_id = ?",
                (guild_id,)
            )
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Ошибка получения списка доверенных лиц: {e}")
            return []
    
    # Методы для работы с действиями пользователей
    def log_action(self, guild_id, user_id, action_type):
        """Логирование действия пользователя"""
        try:
            self.cursor.execute(
                "INSERT INTO user_actions (guild_id, user_id, action_type) VALUES (?, ?, ?)",
                (guild_id, user_id, action_type)
            )
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка логирования действия: {e}")
            return False
    
    def count_user_actions(self, guild_id, user_id, action_type, hours=24):
        """Подсчет количества действий пользователя за указанный период"""
        try:
            time_threshold = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute(
                """
                SELECT COUNT(*) FROM user_actions 
                WHERE guild_id = ? AND user_id = ? AND action_type = ? AND timestamp > ?
                """,
                (guild_id, user_id, action_type, time_threshold)
            )
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Ошибка подсчета действий пользователя: {e}")
            return 0
    
    # Методы для работы с изображениями серверов
    def set_server_image(self, guild_id, image_url):
        """Установка изображения для сервера"""
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO server_images (guild_id, image_url, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (guild_id, image_url)
            )
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка установки изображения сервера: {e}")
            return False
    
    def get_server_image(self, guild_id):
        """Получение URL изображения для сервера"""
        try:
            self.cursor.execute(
                "SELECT image_url FROM server_images WHERE guild_id = ?",
                (guild_id,)
            )
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Ошибка получения изображения сервера: {e}")
            return None
