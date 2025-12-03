# auth.py - Funções de autenticação e manipulação de usuários
# Centrali za a lógica de login, registro e verificação de credenciais

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from db import db, Usuario
from werkzeug.security import generate_password_hash

# ===== Blueprint de autenticação =====
# Agrupa as rotas de autenticação em um módulo separado
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Rota de login
    GET: Exibe a página de login
    POST: Processa o formulário e autentica o usuário
    """
  
    
    if request.method == 'POST':
        # Recupera dados do formulário
        username = request.form.get('username', '').strip()
        senha = request.form.get('senha', '')
        
        # Validação básica
        if not username or not senha:
            flash('Username e senha são obrigatórios', 'danger')
            return redirect(url_for('auth.login'))
        
        # Busca o usuário no banco de dados
        usuario = Usuario.query.filter_by(username=username).first()
        
        # Verifica se o usuário existe e se a senha está correta
        if usuario and usuario.verificar_senha(senha):
            # Efetua o login usando flask_login
            login_user(usuario)
            flash(f'Bem-vindo, {username}!', 'success')
            
            # Redireciona para a página anterior (referrer) ou dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('visualizar_compras'))
        else:
            # Login falhou
            flash('Username ou senha inválidos', 'danger')
    
    # Renderiza a página de login
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """
    Rota de logout
    Remove a sessão do usuário e redireciona para login
    """
    logout_user()
    flash('Você foi desconectado', 'info')
    return redirect(url_for('auth.login'))


def criar_usuario_padrao():
    """
    Função auxiliar para criar um usuário padrão
    Útil para testes no Replit
    """
    # Verifica se já existe um usuário
    usuario_existente = Usuario.query.filter_by(username='admin').first()
    
    if not usuario_existente:
        try:
            # Cria um novo usuário
            novo_usuario = Usuario(username='admin')
            novo_usuario.set_senha('admin123')  # Mude esta senha em produção!
            
            # Adiciona ao banco de dados
            db.session.add(novo_usuario)
            db.session.commit()
            
            print("✓ Usuário padrão 'admin' criado com sucesso (senha: admin123)")
            return True
        except Exception as e:
            print(f"✗ Erro ao criar usuário padrão: {e}")
            db.session.rollback()
            return False
    else:
        print("✓ Usuário padrão já existe")
        return True
