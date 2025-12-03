# db.py - Modelos do banco de dados e inicialização do SQLAlchemy
# Define as tabelas usuario, compra e gestao_estoque como modelos ORM

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# ===== Instância do SQLAlchemy =====
db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    """
    Modelo da tabela 'usuario'
    Representa um usuário do sistema com autenticação
    """
    __tablename__ = 'usuario'
    
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    
    # Relacionamento com outras tabelas (para futuro uso)
    compras = db.relationship('Compra', backref='usuario', lazy=True)
    estoques = db.relationship('GestaoEstoque', backref='usuario', lazy=True)
    
    def get_id(self):
        """Retorna o ID do usuário para flask_login"""
        return str(self.id_usuario)
    
    def set_senha(self, senha):
        """
        Define a senha do usuário com hash bcrypt
        A função generate_password_hash já usa bcrypt internamente
        """
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        """
        Verifica se a senha fornecida corresponde ao hash armazenado
        Retorna True se válido, False caso contrário
        """
        return check_password_hash(self.senha_hash, senha)
    
    def __repr__(self):
        return f'<Usuario {self.username}>'


class Compra(db.Model):
    """
    Modelo da tabela 'compra'
    Representa um lançamento de compra (somente leitura na web)
    """
    __tablename__ = 'compra'
    
    id_compra = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cod = db.Column(db.Integer, nullable=False, index=True)  # Código do produto
    descricao = db.Column(db.String(255), nullable=False)    # Descrição do produto
    peso = db.Column(db.DECIMAL(15, 3), nullable=False)      # Quantidade/peso comprado
    valor = db.Column(db.DECIMAL(15, 2), nullable=False)     # Valor unitário
    total = db.Column(db.DECIMAL(15, 2), nullable=False)     # Valor total (peso * valor)
    data = db.Column(db.Date, nullable=True, index=True)     # Data da compra
    conta_estoque = db.Column(db.Integer, nullable=True, index=True)  # Número da conta de estoque
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=True)
    
    def __repr__(self):
        return f'<Compra {self.id_compra}: {self.descricao}>'


class GestaoEstoque(db.Model):
    """
    Modelo da tabela 'gestao_estoque'
    Representa um movimento de estoque (somente leitura na web)
    """
    __tablename__ = 'gestao_estoque'
    
    id_estoque = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cod = db.Column(db.Integer, nullable=False, index=True)   # Código do produto
    descricao = db.Column(db.String(255), nullable=False)     # Descrição do produto
    peso = db.Column(db.DECIMAL(15, 3), nullable=False)       # Peso do produto
    valor_unitario = db.Column(db.DECIMAL(15, 2), nullable=False)  # Valor unitário
    valor_total = db.Column(db.DECIMAL(15, 2), nullable=False)     # Valor total
    peso_fisico = db.Column(db.DECIMAL(15, 3), nullable=False)     # Peso físico do movimento
    entrada = db.Column(db.DECIMAL(15, 3), nullable=False)         # Quantidade de entrada
    saida = db.Column(db.DECIMAL(15, 3), nullable=False)           # Quantidade de saída
    data = db.Column(db.Date, nullable=True, index=True)           # Data do movimento
    conta_estoque = db.Column(db.Integer, nullable=True, index=True)  # Número da conta de estoque
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=True)
    
    def __repr__(self):
        return f'<GestaoEstoque {self.id_estoque}: {self.descricao}>'
