# main.py - Aplicação principal Flask
# Ponto de entrada da aplicação, inicializa Flask, banco de dados e rotas

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_required, current_user
from config import config
from db import db, Usuario, Compra, GestaoEstoque
from auth import auth_bp, criar_usuario_padrao
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, text
import os

# ===== Inicialização da aplicação Flask =====
app = Flask(__name__)

# ===== Carrega configurações baseado no ambiente =====
app.config.from_object(config)

# ===== Inicializa extensões Flask =====
db.init_app(app)

# ===== Configuração de login =====
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # Redireciona para login se não autenticado
login_manager.login_message = 'Por favor, faça login para acessar esta página'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def carrega_usuario(id_usuario):
    """Carrega o usuário da sessão pelo ID"""
    return Usuario.query.get(int(id_usuario))

# ===== Registro de blueprints =====
app.register_blueprint(auth_bp)

# ===== Criação do contexto da aplicação =====
with app.app_context():
    # Cria todas as tabelas definidas nos modelos
    db.create_all()
    # Cria usuário padrão se não existir
    criar_usuario_padrao()

# ====== FUNÇÕES AUXILIARES ======

def formatar_decimal(valor, casas=2):
    """Converte Decimal em float para JSON"""
    if valor is None:
        return 0.0
    return float(round(Decimal(str(valor)), casas))


def obter_filtros_request():
    """
    Extrai os filtros do request (GET/POST)
    Retorna um dicionário com data_inicial, data_final, conta_estoque, produto
    """
    filtros = {
        'data_inicial': request.args.get('data_inicial', '') or request.form.get('data_inicial', ''),
        'data_final': request.args.get('data_final', '') or request.form.get('data_final', ''),
        'conta_estoque': request.args.get('conta_estoque', '') or request.form.get('conta_estoque', ''),
        'produto': request.args.get('produto', '') or request.form.get('produto', ''),
        'filtro_tipo': request.args.get('filtro_tipo', 'todos') or request.form.get('filtro_tipo', 'todos')
    }
    
    # Converte datas de string para objeto date se fornecidas
    try:
        if filtros['data_inicial']:
            filtros['data_inicial'] = datetime.strptime(filtros['data_inicial'], '%Y-%m-%d').date()
        else:
            # Se não fornecida, usa 1 ano atrás
            filtros['data_inicial'] = datetime.now().date() - timedelta(days=365)
    except:
        filtros['data_inicial'] = datetime.now().date() - timedelta(days=365)
    
    try:
        if filtros['data_final']:
            filtros['data_final'] = datetime.strptime(filtros['data_final'], '%Y-%m-%d').date()
        else:
            # Se não fornecida, usa hoje
            filtros['data_final'] = datetime.now().date()
    except:
        filtros['data_final'] = datetime.now().date()
    
    return filtros


def aplicar_filtros_compra(query, filtros):
    """
    Aplica filtros à query de compras
    Recebe a query e um dicionário de filtros
    Retorna a query modificada com WHERE clauses
    """
    # Filtro por data
    if filtros['data_inicial']:
        query = query.filter(Compra.data >= filtros['data_inicial'])
    
    if filtros['data_final']:
        query = query.filter(Compra.data <= filtros['data_final'])
    
    # Filtro por conta de estoque
    if filtros['conta_estoque']:
        try:
            conta = int(filtros['conta_estoque'])
            query = query.filter(Compra.conta_estoque == conta)
        except:
            pass
    
    # Filtro por produto (busca em descricao ou cod)
    if filtros['produto']:
        termo = f"%{filtros['produto']}%"
        query = query.filter(
            (Compra.descricao.ilike(termo)) | 
            (Compra.cod.cast(db.String).ilike(termo))
        )
    
    return query


def aplicar_filtros_estoque(query, filtros):
    """
    Aplica filtros à query de estoque
    Semelhante a aplicar_filtros_compra, mas para a tabela gestao_estoque
    """
    # Filtro por data
    if filtros['data_inicial']:
        query = query.filter(GestaoEstoque.data >= filtros['data_inicial'])
    
    if filtros['data_final']:
        query = query.filter(GestaoEstoque.data <= filtros['data_final'])
    
    # Filtro por conta de estoque
    if filtros['conta_estoque']:
        try:
            conta = int(filtros['conta_estoque'])
            query = query.filter(GestaoEstoque.conta_estoque == conta)
        except:
            pass
    
    # Filtro por produto
    if filtros['produto']:
        termo = f"%{filtros['produto']}%"
        query = query.filter(
            (GestaoEstoque.descricao.ilike(termo)) | 
            (GestaoEstoque.cod.cast(db.String).ilike(termo))
        )
    
    # Filtro por tipo (Todos/Entradas/Saídas)
    if filtros['filtro_tipo'] == 'entradas':
        query = query.filter(GestaoEstoque.entrada > 0)
    elif filtros['filtro_tipo'] == 'saidas':
        query = query.filter(GestaoEstoque.saida > 0)
    
    return query


# ====== ROTAS PRINCIPAIS ======

@app.route('/')
def index():
    """
    Rota raiz - redireciona para compras ou login
    """
    if current_user.is_authenticated:
        return redirect(url_for('visualizar_compras'))
    return redirect(url_for('auth.login'))




@app.route('/compras/por-periodo')
@login_required
def compras_por_periodo():
    """
    Página: Total de compras agrupado por período (data)
    Exibe em tabela e gráfico
    """
    # Obtém filtros
    filtros = obter_filtros_request()
    
    # ===== Query para agrupar compras por data =====
    resultado = db.session.query(
        Compra.data,
        func.count(Compra.id_compra).label('quantidade'),
        func.sum(Compra.total).label('total')
    ).filter(
        Compra.data >= filtros['data_inicial'],
        Compra.data <= filtros['data_final']
    ).group_by(Compra.data).order_by(Compra.data.desc()).all()
    
    # ===== Processa resultados =====
    dados_tabela = []
    for data, qtd, total in resultado:
        if data:  # Verifica se data não é nula
            ticket = formatar_decimal(total / qtd) if qtd > 0 else 0
            dados_tabela.append({
                'data': data.strftime('%d/%m/%Y'),
                'quantidade': qtd,
                'total': formatar_decimal(total),
                'ticket_medio': ticket
            })
    
    # ===== Prepara dados para gráfico =====
    labels_grafico = [d['data'] for d in dados_tabela]
    valores_grafico = [d['total'] for d in dados_tabela]
    
    return render_template('compras_por_periodo.html', 
                          dados=dados_tabela,
                          labels_grafico=labels_grafico,
                          valores_grafico=valores_grafico,
                          filtros=filtros)


@app.route('/compras/ranking-produtos')
@login_required
def compras_ranking_produtos():
    """
    Página: Ranking de produtos mais comprados
    Agrupa por produto e exibe quantidade, valor total e preço médio
    """
    # Obtém filtros
    filtros = obter_filtros_request()
    
    # ===== Query para agrupar compras por produto (descricao) =====
    resultado = db.session.query(
        Compra.cod,
        Compra.descricao,
        func.sum(Compra.peso).label('quantidade_total'),
        func.sum(Compra.total).label('valor_total'),
        func.avg(Compra.valor).label('preco_medio')
    ).filter(
        Compra.data >= filtros['data_inicial'],
        Compra.data <= filtros['data_final']
    )
    
    # Aplica filtro de produto se fornecido
    if filtros['produto']:
        termo = f"%{filtros['produto']}%"
        resultado = resultado.filter(
            (Compra.descricao.ilike(termo)) | 
            (Compra.cod.cast(db.String).ilike(termo))
        )
    
    resultado = resultado.group_by(Compra.cod, Compra.descricao)\
                        .order_by(func.sum(Compra.peso).desc())\
                        .limit(20).all()  # Top 20
    
    # ===== Processa resultados =====
    dados_tabela = []
    for cod, descricao, qtd, valor, preco in resultado:
        dados_tabela.append({
            'cod': cod,
            'descricao': descricao,
            'quantidade_total': formatar_decimal(qtd or 0, 3),
            'valor_total': formatar_decimal(valor or 0),
            'preco_medio': formatar_decimal(preco or 0)
        })
    
    return render_template('compras_ranking.html', 
                          dados=dados_tabela,
                          filtros=filtros)


@app.route('/compras/preco-medio')
@login_required
def compras_preco_medio():
    """
    Página: Análise de preço médio
    Dois modos: evolução mensal e comparação entre produtos
    """
    # Obtém filtros
    filtros = obter_filtros_request()
    modo = request.args.get('modo', 'mensal')  # 'mensal' ou 'produto'
    
    if modo == 'mensal':
        # ===== Evolução mensal de preço médio =====
        resultado = db.session.query(
            func.year(Compra.data).label('ano'),
            func.month(Compra.data).label('mes'),
            func.count(Compra.id_compra).label('quantidade'),
            func.avg(Compra.valor).label('preco_medio'),
            func.sum(Compra.total).label('valor_total')
        ).filter(
            Compra.data >= filtros['data_inicial'],
            Compra.data <= filtros['data_final']
        ).group_by(
            func.year(Compra.data),
            func.month(Compra.data)
        ).order_by(
            func.year(Compra.data).desc(),
            func.month(Compra.data).desc()
        ).all()
        
        # Processa resultados
        dados_tabela = []
        for ano, mes, qtd, preco, valor in resultado:
            nome_mes = datetime(ano, mes, 1).strftime('%B/%Y')
            dados_tabela.append({
                'periodo': nome_mes,
                'quantidade': qtd,
                'preco_medio': formatar_decimal(preco),
                'valor_total': formatar_decimal(valor)
            })
    
    else:  # modo == 'produto'
        # ===== Comparação de preço médio por produto =====
        resultado = db.session.query(
            Compra.cod,
            Compra.descricao,
            func.avg(Compra.valor).label('preco_medio'),
            func.sum(Compra.total).label('valor_total'),
            func.count(Compra.id_compra).label('quantidade')
        ).filter(
            Compra.data >= filtros['data_inicial'],
            Compra.data <= filtros['data_final']
        ).group_by(Compra.cod, Compra.descricao)\
         .order_by(func.avg(Compra.valor).desc())\
         .limit(15).all()
        
        dados_tabela = []
        for cod, descricao, preco, valor, qtd in resultado:
            dados_tabela.append({
                'cod': cod,
                'descricao': descricao,
                'preco_medio': formatar_decimal(preco),
                'valor_total': formatar_decimal(valor),
                'quantidade': qtd
            })
    
    return render_template('compras_preco_medio.html', 
                          dados=dados_tabela,
                          modo=modo,
                          filtros=filtros)


@app.route('/compras/comparacao-meses')
@login_required
def compras_comparacao_meses():
    """
    Página: Comparação entre meses
    Agrupa compras por mês e calcula crescimento percentual
    """
    # Obtém filtros
    filtros = obter_filtros_request()
    
    # ===== Query para agrupar por mês =====
    resultado = db.session.query(
        func.year(Compra.data).label('ano'),
        func.month(Compra.data).label('mes'),
        func.count(Compra.id_compra).label('quantidade'),
        func.sum(Compra.total).label('total')
    ).filter(
        Compra.data >= filtros['data_inicial'],
        Compra.data <= filtros['data_final']
    ).group_by(
        func.year(Compra.data),
        func.month(Compra.data)
    ).order_by(
        func.year(Compra.data).asc(),
        func.month(Compra.data).asc()
    ).all()
    
    # ===== Processa resultados e calcula crescimento =====
    dados_tabela = []
    mes_anterior_total = 0
    
    for ano, mes, qtd, total in resultado:
        total_float = formatar_decimal(total)
        
        # Calcula crescimento percentual
        if mes_anterior_total > 0:
            crescimento = ((total_float - mes_anterior_total) / mes_anterior_total) * 100
        else:
            crescimento = 0
        
        nome_mes = datetime(ano, mes, 1).strftime('%B %Y')
        
        dados_tabela.append({
            'mes': nome_mes,
            'total': total_float,
            'quantidade': qtd,
            'crescimento': round(crescimento, 2),
            'crescimento_color': 'green' if crescimento >= 0 else 'red'
        })
        
        mes_anterior_total = total_float
    
    return render_template('compras_comparacao_meses.html', 
                          dados=dados_tabela,
                          filtros=filtros)


@app.route('/compras/top-10')
@login_required
def compras_top_10():
    """
    Página: Top 10 maiores compras
    Lista as 10 maiores compras por valor total
    """
    # Obtém filtros
    filtros = obter_filtros_request()
    
    # ===== Query para os top 10 =====
    resultado = db.session.query(Compra).filter(
        Compra.data >= filtros['data_inicial'],
        Compra.data <= filtros['data_final']
    ).order_by(Compra.total.desc()).limit(10).all()
    
    # ===== Processa resultados =====
    dados_tabela = []
    for i, compra in enumerate(resultado, 1):
        dados_tabela.append({
            'posicao': i,
            'data': compra.data.strftime('%d/%m/%Y') if compra.data else '-',
            'descricao': compra.descricao,
            'quantidade': formatar_decimal(compra.peso, 3),
            'valor_unitario': formatar_decimal(compra.valor),
            'total': formatar_decimal(compra.total),
            'conta': compra.conta_estoque or '-'
        })
    
    return render_template('compras_top_10.html', 
                          dados=dados_tabela,
                          filtros=filtros)


@app.route('/compras')
@login_required
def visualizar_compras():
    """
    Página principal: Visualização de compras
    Lista todas as compras com filtros por data, conta e produto
    """
    # Obtém filtros
    filtros = obter_filtros_request()
    
    # ===== Query base para compras =====
    query = Compra.query.filter(
        Compra.data >= filtros['data_inicial'],
        Compra.data <= filtros['data_final']
    )
    
    # Aplica filtro de conta de estoque se fornecido
    if filtros['conta_estoque']:
        try:
            conta = int(filtros['conta_estoque'])
            query = query.filter(Compra.conta_estoque == conta)
        except:
            pass
    
    # Aplica filtro de produto (busca em descricao ou cod)
    if filtros['produto']:
        termo = f"%{filtros['produto']}%"
        query = query.filter(
            (Compra.descricao.ilike(termo)) | 
            (Compra.cod.cast(db.String).ilike(termo))
        )
    
    # Ordena por data descrescente
    resultado = query.order_by(Compra.data.desc()).all()
    
    # ===== Processa resultados para exibição =====
    dados_tabela = []
    for compra in resultado:
        dados_tabela.append({
            'data': compra.data.strftime('%d/%m/%Y') if compra.data else '-',
            'cod': compra.cod,
            'descricao': compra.descricao,
            'peso': formatar_decimal(compra.peso, 3),
            'valor_unitario': formatar_decimal(compra.valor),
            'total': formatar_decimal(compra.total),
            'conta': compra.conta_estoque or '-'
        })
    
    return render_template('compras.html', 
                          dados=dados_tabela,
                          filtros=filtros)


@app.route('/estoque')
@login_required
def visualizar_estoque():
    """
    Página: Visualização de estoque
    Lista movimentos de estoque com filtros e cálculo de saldo
    """
    # Obtém filtros
    filtros = obter_filtros_request()
    
    # ===== Query base para movimentos de estoque =====
    query = GestaoEstoque.query.filter(
        GestaoEstoque.data >= filtros['data_inicial'],
        GestaoEstoque.data <= filtros['data_final']
    )
    
    # Aplica filtro de conta de estoque se fornecido
    if filtros['conta_estoque']:
        try:
            conta = int(filtros['conta_estoque'])
            query = query.filter(GestaoEstoque.conta_estoque == conta)
        except:
            pass
    
    # Aplica filtro de produto
    if filtros['produto']:
        termo = f"%{filtros['produto']}%"
        query = query.filter(
            (GestaoEstoque.descricao.ilike(termo)) | 
            (GestaoEstoque.cod.cast(db.String).ilike(termo))
        )
    
    # Aplica filtro de tipo (Todos/Entradas/Saídas)
    if filtros['filtro_tipo'] == 'entradas':
        query = query.filter(GestaoEstoque.entrada > 0)
    elif filtros['filtro_tipo'] == 'saidas':
        query = query.filter(GestaoEstoque.saida > 0)
    
    # Ordena por data descrescente
    resultado = query.order_by(GestaoEstoque.data.desc()).all()
    
    # ===== Processa resultados =====
    dados_tabela = []
    for estoque in resultado:
        saldo = formatar_decimal(estoque.entrada - estoque.saida, 3)
        dados_tabela.append({
            'data': estoque.data.strftime('%d/%m/%Y') if estoque.data else '-',
            'cod': estoque.cod,
            'descricao': estoque.descricao,
            'peso': formatar_decimal(estoque.peso, 3),
            'valor_unitario': formatar_decimal(estoque.valor_unitario),
            'valor_total': formatar_decimal(estoque.valor_total),
            'peso_fisico': formatar_decimal(estoque.peso_fisico, 3),
            'entrada': formatar_decimal(estoque.entrada, 3),
            'saida': formatar_decimal(estoque.saida, 3),
            'saldo': saldo,
            'conta': estoque.conta_estoque or '-'
        })
    
    return render_template('estoque.html', 
                          dados=dados_tabela,
                          filtros=filtros)


@app.errorhandler(404)
def erro_404(error):
    """Tratamento de erro 404 (página não encontrada)"""
    return render_template('erro_404.html'), 404


@app.errorhandler(500)
def erro_500(error):
    """Tratamento de erro 500 (erro interno do servidor)"""
    return render_template('erro_500.html'), 500


# ====== PONTO DE ENTRADA DA APLICAÇÃO ======
if __name__ == '__main__':
    # Executa a aplicação Flask
    # debug=True recarrega automaticamente ao detectar mudanças
    # host='0.0.0.0' permite acesso de qualquer IP (necessário no Replit)
    app.run(debug=True, host='0.0.0.0', port=5000)
