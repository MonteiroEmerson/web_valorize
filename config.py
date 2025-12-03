# config.py - Configurações centralizadas da aplicação
# Este arquivo carrega as variáveis de ambiente e configura a aplicação

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Carrega as variáveis do arquivo .env
load_dotenv()

class Config:
    """Classe de configuração padrão"""
    
    # ===== Chave secreta para sessões Flask =====
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # ===== Configuração do banco de dados MySQL =====
    DB_HOST = os.getenv('DB_HOST', '192.168.1.158')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'eres')
    _raw_password = os.getenv('DB_PASSWORD', 'Pkmd1357@')
    DB_PASSWORD = quote_plus(_raw_password)  # Codifica caracteres especiais
    DB_NAME = os.getenv('DB_NAME', 'valorize')
    
    # URL de conexão SQLAlchemy para MySQL
    # Formato: mysql+pymysql://usuario:senha@host:porta/database
    # Usando mysql-connector como driver
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    
    # ===== Configurações SQLAlchemy =====
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Desabilita avisos desnecessários
    SQLALCHEMY_ECHO = False  # Mude para True se quiser ver as queries SQL no console
    
    # ===== Configurações de sessão =====
    SESSION_COOKIE_SECURE = False  # Mude para True em produção com HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Protege contra XSS
    PERMANENT_SESSION_LIFETIME = 3600  # Sessão dura 1 hora

# Classe para desenvolvimento (com debug ativado)
class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

# Classe para produção
class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

# Classe para testes
class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    # Usa banco de dados em memória para testes
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Define qual configuração usar baseado em variável de ambiente
config_name = os.getenv('FLASK_ENV', 'development')
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}.get(config_name, DevelopmentConfig)
