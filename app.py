import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import text
from PIL import Image
import numpy as np
import io
import base64

# CONFIGURAÇÃO MANDATÓRIA: Primeira linha para ativar o modo tela cheia nativo
st.set_page_config(page_title="Datalake Comercial Executivo", layout="wide")

# DEFESA GLOBLAL CONTRA NAMEERROR
titulo_grafico_tempo = ""

# DICIONÁRIO CORPORATIVO GLOBAL DE TRADUÇÃO DE MESES
meses_pt = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
    7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

# ==========================================================
# 🎯 MOTOR DE TRATAMENTO DE IMAGEM: DARK MODE AUTOMÁTICO
# ==========================================================
@st.cache_data
def obter_logo_sem_fundo_comercial():
    try:
        img = Image.open("Logo.jpeg").convert("RGBA")
        data = np.array(img)
        
        # 1. Detecta o fundo branco e clareia para remoção absoluta
        fundo_branco = (data[:, :, 0] > 220) & (data[:, :, 1] > 220) & (data[:, :, 2] > 220)
        
        # 2. Detecta as letras pretas (ECO representação)
        letras_pretas = (data[:, :, 0] < 120) & (data[:, :, 1] < 120) & (data[:, :, 2] < 120) & (~fundo_branco)
        
        # 3. Transforma fundo em transparente e texto preto em BRANCO CORPORATIVO
        data[fundo_branco] = [0, 0, 0, 0]
        data[letras_pretas] = [248, 250, 252, 255] # #F8FAFC
        
        return Image.fromarray(data)
    except Exception:
        return None

def converter_imagem_base64(img):
    if img is None: return ""
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Inicializa e converte a logo tratada
logo_eco = obter_logo_sem_fundo_comercial()
logo_b64 = converter_imagem_base64(logo_eco)

# ==========================================================
# 🔐 1. ENGINE DE AUTENTICAÇÃO REAL COM PERSISTÊNCIA DE URL
# ==========================================================
if "autenticado" not in st.session_state: st.session_state["autenticado"] = False
if "exigir_reset" not in st.session_state: st.session_state["exigir_reset"] = False
if "usuario_atual" not in st.session_state: st.session_state["usuario_atual"] = ""
if "expanded_items" not in st.session_state: st.session_state["expanded_items"] = set()
if "df_key_counter" not in st.session_state: st.session_state["df_key_counter"] = 0

# MOTOR DE AUTO-LOGIN: Lê o token seguro após um F5
if not st.session_state["autenticado"] and "usr" in st.query_params:
    email_salvo = st.query_params["usr"]
    conn = st.connection("postgresql", type="sql")
    check_df = conn.query("SELECT status FROM usuarios WHERE email = :email", params={"email": email_salvo}, ttl=0)
    if not check_df.empty and check_df.iloc[0]['status'] == "Ativo":
        st.session_state["autenticado"] = True
        st.session_state["usuario_atual"] = email_salvo

if not st.session_state["autenticado"]:
    st.markdown("""
        <style>
        .stApp { background-color: #050810; font-family: 'Inter', sans-serif; }
        div[data-testid="stHeader"], header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        
        /* Customiza o bloco do container nativo para ser o card de login */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #0E1320 !important;
            border: 1px solid #1E293B !important;
            border-radius: 16px !important;
            padding: 32px !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5) !important;
        }
        
        .stTextInput input {
            background-color: #050810 !important; color: #F9FAFB !important;
            border: 1px solid #1E293B !important; border-radius: 8px !important;
            padding: 12px 16px !important; font-size: 0.95rem !important;
        }
        .stTextInput input:focus { border-color: #2563EB !important; box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15) !important; }
        .stTextInput label { color: #94A3B8 !important; font-size: 0.85rem !important; font-weight: 500 !important; }
        .stCheckbox label p { color: #94A3B8 !important; font-size: 0.9rem !important; font-weight: 500; }
        div.stButton > button {
            background-color: #2563EB !important; color: #FFFFFF !important;
            font-weight: 600 !important; font-size: 0.95rem !important;
            border-radius: 8px !important; border: none !important; padding: 12px 0px !important;
        }
        div.stButton > button:hover { background-color: #1D4ED8 !important; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div style="height: 12vh;"></div>', unsafe_allow_html=True)
    
    _, col_login_wrapper, _ = st.columns([1, 1.1, 1])
    
    with col_login_wrapper:
        with st.container(border=True):
            if logo_eco is not None:
                st.markdown(f'<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 24px; padding-top: 10px;"><img src="data:image/png;base64,{logo_b64}" style="max-width: 85%; height: auto;"/></div>', unsafe_allow_html=True)
                
            conn = st.connection("postgresql", type="sql")
            
            if st.session_state["exigir_reset"]:
                st.markdown("<h2 style='text-align: center; color: #F8FAFC; font-weight: 700; margin-bottom:4px;'>Definir nova senha</h2>", unsafe_allow_html=True)
                nova_senha = st.text_input("Nova senha", type="password", key="new_pwd")
                confirma_senha = st.text_input("Confirme a nova senha", type="password", key="conf_pwd")
                
                if st.button("Salvar e Acessar", use_container_width=True):
                    if not nova_senha or nova_senha == "Mudar123!":
                        st.markdown("<p style='color:#EF4444; font-size:0.85rem; text-align:center;'>❌ Escolha uma senha diferente.</p>", unsafe_allow_html=True)
                    elif nova_senha == confirma_senha:
                        with conn.session as session:
                            session.execute(
                                text("UPDATE usuarios SET senha = :senha, provisoria = :provisoria WHERE email = :email"), 
                                {"senha": nova_senha, "provisoria": False, "email": st.session_state["usuario_atual"]}
                            )
                            session.commit()
                        st.session_state["autenticado"] = True
                        st.session_state["exigir_reset"] = False
                        st.success("Senha alterada!")
                        st.rerun()
                    else:
                        st.markdown("<p style='color:#EF4444; font-size:0.85rem; text-align:center;'>❌ As senhas não coincidem.</p>", unsafe_allow_html=True)
            else:
                st.markdown("<h2 style='text-align: center; color: #F8FAFC; font-weight: 700; margin-top: 0px; margin-bottom: 4px; font-size: 1.75rem;'>Fazer login</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #94A3B8; font-size:0.95rem; margin-bottom: 24px;'>Prosseguir para o Datalake Executivo</p>", unsafe_allow_html=True)
                
                usuario_input = st.text_input("E-mail corporativo", placeholder="diretor@empresa.com")
                senha_input = st.text_input("Digite sua senha", type="password", placeholder="••••••••")
                
                manter_conectado = st.checkbox("Manter-me conectado", value=True)
                st.write("")
                
                if st.button("Próximo", use_container_width=True):
                    query = "SELECT senha, provisoria, status FROM usuarios WHERE email = :email"
                    user_df = conn.query(query, params={"email": usuario_input.strip()}, ttl=0)
                    
                    if not user_df.empty:
                        if user_df.iloc[0]['status'] != "Ativo":
                            st.markdown("<p style='color: #EF4444; font-size:0.85rem; text-align:center;'>🚫 Usuário revogado.</p>", unsafe_allow_html=True)
                        elif senha_input == user_df.iloc[0]['senha']:
                            st.session_state["usuario_atual"] = usuario_input.strip()
                            if user_df.iloc[0]['provisoria']:
                                st.session_state["exigir_reset"] = True
                                st.rerun()
                            else:
                                st.session_state["autenticado"] = True
                                if manter_conectado:
                                    st.query_params["usr"] = usuario_input.strip()
                                st.rerun()
                        else:
                            st.markdown("<p style='color: #EF4444; font-size:0.85rem; text-align:center;'>❌ Senha incorreta.</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color: #EF4444; font-size:0.85rem; text-align:center;'>❌ Usuário não localizado.</p>", unsafe_allow_html=True)
                        
    st.stop()

# ==========================================================
# 2. FOLHA DE ESTILO CORPORATIVA (SIDEBAR, KPIS E HEADERS)
# ==========================================================
st.markdown("""
    <style>
    .block-container { 
        padding-top: 4.5rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 98% !important;
    }
    
    .kpi-card {
        background: #0E1320; border: 1px solid #1E293B; border-radius: 14px; padding: 24px; position: relative; overflow: hidden;
        transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
    }
    .kpi-card:hover { transform: translateY(-3px); border-color: #334155; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2); }
    .kpi-card.blue-accent::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #2563EB, #60A5FA); }
    .kpi-card.emerald-accent::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #059669, #34D399); }
    .kpi-card.orange-accent::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #EA580C, #FB923C); }
    .kpi-card.purple-accent::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #7C3AED, #A78BFA); }
    
    .kpi-title { color: #94A3B8; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; }
    .kpi-value { color: #F8FAFC; font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1; }
    .kpi-footer { display: flex; align-items: center; margin-top: 16px; font-size: 0.85rem; }
    .badge-positive { background-color: rgba(16, 185, 129, 0.1); color: #10B981; padding: 4px 10px; border-radius: 6px; font-weight: 600; margin-right: 10px; }
    .badge-negative { background-color: rgba(239, 68, 68, 0.1); color: #EF4444; padding: 4px 10px; border-radius: 6px; font-weight: 600; margin-right: 10px; }
    .kpi-ly-text { color: #64748B; font-size: 0.8rem; font-weight: 500; }
    
    .chart-header { display: flex; align-items: center; margin-bottom: 10px !important; }
    .chart-icon-box { background: #1E293B; padding: 8px; border-radius: 8px; margin-right: 12px; display:flex; align-items:center; justify-content:center;}
    .chart-title-text { margin: 0; color: #F8FAFC; font-size: 1.05rem; font-weight: 600; letter-spacing: 0.01em;}
    
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        background-color: transparent !important; color: #94A3B8 !important;
        border-radius: 6px !important; padding: 8px 12px !important; margin-bottom: 3px !important; width: 100% !important; display: flex !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover { background-color: rgba(255, 255, 255, 0.03) !important; color: #F8FAFC !important; }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"] { background-color: #1E3A8A !important; color: #3B82F6 !important; font-weight: 600 !important; }
    div[role="radiogroup"] label span:first-child { display: none !important; }
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        overflow: visible !important;
    }
    
    div[data-testid="stDataFrame"]::-webkit-scrollbar,
    .stDataFrame > div::-webkit-scrollbar {
        display: none !important;
        width: 0px !important;
        height: 0px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================================
# TIMING & CURRENCY STRING CONTROLLERS
# ==========================================================
def formatar_moeda_br(valor):
    if valor >= 1_000_000_000: return f"R$ {valor/1_000_000_000:.1f} Bi".replace('.', ',')
    elif valor >= 1_000_000: return f"R$ {valor/1_000_000:.1f} Mi".replace('.', ',')
    elif valor >= 1_000: return f"R$ {valor/1_000:.1f} Mil".replace('.', ',')
    else: return f"R$ {valor:.0f}"

def formatar_moeda_br_completo(valor):
    return f"R$ {valor:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')

# ==========================================================
# FABRICA DA MATRIZ DE DEZESSETE COLUNAS COM TOTAL BI NATIVO
# ==========================================================
def gerar_tabela_analitica_padrao(df_at, df_ly_raw, coluna_grupo, incluir_total=True):
    total_faturamento_atual = df_at['Total'].sum()
    cols_grupo = [coluna_grupo] if isinstance(coluna_grupo, str) else coluna_grupo
    
    df_at_copy = df_at.copy()
    if 'Mes_Ano' in cols_grupo and not df_at_copy.empty:
        df_at_copy['Mes_Ano'] = df_at_copy['Data'].dt.strftime('%Y-%m')
    
    if not df_at_copy.empty:
        agg_at = df_at_copy.groupby(cols_grupo).agg(Vendas=('Total', 'sum'), Qtd_de_Itens=('Quantidade', 'sum'), Pedidos=('Ped_Cliente', 'nunique')).reset_index()
    else:
        agg_at = pd.DataFrame(columns=cols_grupo + ['Vendas', 'Qtd_de_Itens', 'Pedidos'])
        
    df_ly = df_ly_raw.copy()
    if 'Mes_Ano' in cols_grupo and not df_ly.empty:
        df_ly['Data_Shifted'] = df_ly['Data'].apply(lambda x: x + relativedelta(years=1))
        df_ly['Mes_Ano'] = df_ly['Data_Shifted'].dt.strftime('%Y-%m')
        
    if not df_ly.empty:
        agg_ly = df_ly.groupby(cols_grupo).agg(Vendas_LY=('Total', 'sum'), Itens_LY=('Quantidade', 'sum'), Pedidos_LY=('Ped_Cliente', 'nunique')).reset_index()
    else:
        agg_ly = pd.DataFrame(columns=cols_grupo + ['Vendas_LY', 'Itens_LY', 'Pedidos_LY'])
        
    df_merged = pd.merge(agg_at, agg_ly, on=cols_grupo, how='outer').fillna(0)
    
    if 'Mes_Ano' in cols_grupo:
        df_merged = df_merged.sort_values('Mes_Ano', ascending=True)
    
    df_merged['Diferença Vendas %'] = df_merged.apply(lambda r: ((r['Vendas'] / r['Vendas_LY']) - 1) * 100 if r['Vendas_LY'] > 0 else (100 if r['Vendas'] > 0 else 0), axis=1)
    df_merged['% de Participação'] = df_merged.apply(lambda r: (r['Vendas'] / total_faturamento_atual) * 100 if total_faturamento_atual > 0 else 0, axis=1)
    df_merged['Diferença Pedidos %'] = df_merged.apply(lambda r: ((r['Pedidos'] / r['Pedidos_LY']) - 1) * 100 if r['Pedidos_LY'] > 0 else (100 if r['Pedidos'] > 0 else 0), axis=1)
    df_merged['Diferença Itens %'] = df_merged.apply(lambda r: ((r['Qtd_de_Itens'] / r['Itens_LY']) - 1) * 100 if r['Itens_LY'] > 0 else (100 if r['Qtd_de_Itens'] > 0 else 0), axis=1)
    
    df_merged['Ticket Medio'] = df_merged.apply(lambda r: r['Vendas'] / r['Qtd_de_Itens'] if r['Qtd_de_Itens'] > 0 else 0, axis=1)
    df_merged['Ticket Medio LY'] = df_merged.apply(lambda r: r['Vendas_LY'] / r['Itens_LY'] if r['Itens_LY'] > 0 else 0, axis=1)
    df_merged['Diferença Ticket %'] = df_merged.apply(lambda r: ((r['Ticket Medio'] / r['Ticket Medio LY']) - 1) * 100 if r['Ticket Medio LY'] > 0 else (100 if r['Ticket Medio'] > 0 else 0), axis=1)
    
    df_merged = df_merged.rename(columns={'Qtd_de_Itens': 'Qtd de Itens', 'Vendas_LY': 'Vendas LY', 'Itens_LY': 'Itens LY', 'Pedidos_LY': 'Pedidos LY'})
    ordem_final = cols_grupo + ['Vendas', 'Vendas LY', 'Diferença Vendas %', '% de Participação', 'Pedidos', 'Pedidos LY', 'Diferença Pedidos %', 'Qtd de Itens', 'Itens LY', 'Diferença Itens %', 'Ticket Medio', 'Ticket Medio LY', 'Diferença Ticket %']
    df_merged = df_merged[ordem_final]
    
    if 'Mes_Ano' in cols_grupo:
        def formatar_linha_mes_pt(val):
            try:
                p = val.split('-')
                return f"{meses_pt[int(p[1])]} - {p[0][2:]}"
            except Exception:
                return val
        df_merged['Mes_Ano'] = df_merged['Mes_Ano'].apply(formatar_linha_mes_pt)
        
    if incluir_total:
        total_row = {cols_grupo[0]: "Total Geral"}
        if len(cols_grupo) > 1:
            for c in cols_grupo[1:]: total_row[c] = ""
            
        total_row['Vendas'] = df_at_copy['Total'].sum()
        total_row['Vendas LY'] = df_ly_raw['Total'].sum()
        total_row['Diferença Vendas %'] = ((total_row['Vendas'] / total_row['Vendas LY']) - 1) * 100 if total_row['Vendas LY'] > 0 else (100 if total_row['Vendas'] > 0 else 0)
        total_row['% de Participação'] = 100.0 if total_row['Vendas'] > 0 else 0
        
        total_row['Pedidos'] = df_at_copy['Ped_Cliente'].nunique()
        total_row['Pedidos LY'] = df_ly_raw['Ped_Cliente'].nunique()
        total_row['Diferença Pedidos %'] = ((total_row['Pedidos'] / total_row['Pedidos LY']) - 1) * 100 if total_row['Pedidos LY'] > 0 else (100 if total_row['Pedidos'] > 0 else 0)
        
        total_row['Qtd de Itens'] = df_at_copy['Quantidade'].sum()
        total_row['Itens LY'] = df_ly_raw['Quantidade'].sum()
        total_row['Diferença Itens %'] = ((total_row['Qtd de Itens'] / total_row['Itens LY']) - 1) * 100 if total_row['Itens LY'] > 0 else (100 if total_row['Qtd de Itens'] > 0 else 0)
        
        tm_at = total_row['Vendas'] / total_row['Qtd de Itens'] if total_row['Qtd de Itens'] > 0 else 0
        tm_ly = total_row['Vendas LY'] / total_row['Itens LY'] if total_row['Itens LY'] > 0 else 0
        total_row['Ticket Medio'] = tm_at
        total_row['Ticket Medio LY'] = tm_ly
        total_row['Diferença Ticket %'] = ((tm_at / tm_ly) - 1) * 100 if tm_ly > 0 else (100 if tm_at > 0 else 0)
        
        df_merged = pd.concat([df_merged, pd.DataFrame([total_row])], ignore_index=True)
    return df_merged

def obter_config_colunas_bi(df, label_principal="Dimensão"):
    def max_safe(col): return float(df[col].max()) if col in df.columns and df[col].max() > 0 else 1.0
    return {
        df.columns[0]: st.column_config.TextColumn(label_principal, alignment="left"),
        "Vendas": st.column_config.ProgressColumn("Vendas", format="R$ %,.2f", min_value=0, max_value=max_safe("Vendas"), color="blue"),
        "Vendas LY": st.column_config.ProgressColumn("Vendas LY", format="R$ %,.2f", min_value=0, max_value=max_safe("Vendas LY"), color="orange"),
        "Diferença Vendas %": st.column_config.NumberColumn("Diferença Vendas %", format="%,.2f%%"),
        "% de Participação": st.column_config.ProgressColumn("% de Participação", format="%,.2f%%", min_value=0, max_value=100, color="blue"),
        "Pedidos": st.column_config.ProgressColumn("Pedidos", format="%d", min_value=0, max_value=max_safe("Pedidos"), color="blue"),
        "Pedidos LY": st.column_config.ProgressColumn("Pedidos LY", format="%d", min_value=0, max_value=max_safe("Pedidos LY"), color="orange"),
        "Diferença Pedidos %": st.column_config.NumberColumn("Diferença Pedidos %", format="%,.2f%%"),
        "Qtd de Itens": st.column_config.ProgressColumn("Qtd de Itens", format="%d", min_value=0, max_value=max_safe("Qtd de Itens"), color="blue"),
        "Itens LY": st.column_config.ProgressColumn("Itens LY", format="%d", min_value=0, max_value=max_safe("Itens LY"), color="orange"),
        "Diferença Itens %": st.column_config.NumberColumn("Diferença Itens %", format="%,.2f%%"),
        "Ticket Medio": st.column_config.ProgressColumn("Ticket Medio", format="R$ %,.2f", min_value=0, max_value=max_safe("Ticket Medio"), color="blue"),
        "Ticket Medio LY": st.column_config.ProgressColumn("Ticket Medio LY", format="R$ %,.2f", min_value=0, max_value=max_safe("Ticket Medio LY"), color="orange"),
        "Diferença Ticket %": st.column_config.NumberColumn("Diferença Ticket %", format="%,.2f%%"),
    }

# ==========================================================
# MOTOR DE CAPTAÇÃO DE DADOS OTIMIZADO (LINK + ABA BASE_VENDAS)
# ==========================================================
@st.cache_data(ttl=600)
def carregar_dados_comerciais():
    colunas_padrao = ['Data', 'Cliente', 'Categoria', 'Subcategoria', 'Fabricante', 'Produto', 'Quantidade', 'Total', 'Ped_Cliente']
    df_vazio = pd.DataFrame(columns=colunas_padrao)
    
    url_csv = "https://docs.google.com/spreadsheets/d/e/2PACX-1vShrCwOpKkCJ9pKpQPVAgeiJ1p-auVIzOaXSIwYsXRuw_B8HYrLpq3Ph4TV96sxJw/pub?sheet=Base_Vendas&output=csv"
    
    try:
        df = pd.read_csv(url_csv)
        df.columns = df.columns.str.strip()
        st.session_state['colunas_brutas'] = list(df.columns)
        
        mapeamento = {
            'data': 'Data', 'mês': 'Data', 'mes': 'Data',
            'cliente': 'Cliente', 'canal': 'Cliente', 'categoria': 'Categoria', 
            'subcategoria': 'Subcategoria', 'fabricante': 'Fabricante', 
            'descrição': 'Produto', 'produto': 'Produto', 'qtde': 'Quantidade', 
            'quantidade': 'Quantidade', 'total': 'Total',
            'ped cliente': 'Ped_Cliente', 'ped_cliente': 'Ped_Cliente', 'pedido': 'Ped_Cliente'
        }
        df.columns = [mapeamento.get(c.lower(), c) for c in df.columns]
        
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce', format='mixed', dayfirst=True)
            df = df.dropna(subset=['Data']).copy()
            
        for col in ['Quantidade', 'Total']:
            if col in df.columns:
                df[col] = df[col].astype(str).replace('R\$', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Força a conversão das colunas de texto para Title Case, limpando vazios e nulos
        for text_col in ['Cliente', 'Categoria', 'Subcategoria', 'Fabricante', 'Produto']:
            if text_col in df.columns:
                df[text_col] = df[text_col].astype(str).str.strip().str.title().replace({'Nan': None, 'None': None, '': None})
        
        for col in colunas_padrao:
            if col not in df.columns: df[col] = pd.Series(dtype='object')
        
        fuso_br = timezone(timedelta(hours=-3))
        st.session_state['ultima_atualizacao'] = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M:%S")
        return df
    except Exception:
        return df_vazio

with st.spinner("🔄 Sincronizando datalake executivo..."):
    df_base = carregar_dados_comerciais()

# ==========================================================
# BARRA LATERAL DE ROTEAMENTO (LOGO PREMIUM)
# ==========================================================
if logo_eco is not None:
    st.sidebar.markdown(f'<div style="display: flex; justify-content: center; align-items: center; padding: 12px 24px 20px 24px;"><img src="data:image/png;base64,{logo_b64}" style="max-width: 90%; height: auto;"/></div>', unsafe_allow_html=True)

st.sidebar.markdown("<h2 style='font-size: 1.25rem; font-weight: 700; margin-bottom: 0px;'>Módulos de Análise</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color: #64748B; font-size: 0.8rem; margin-top: 0px;'>Executive Suite v4.0</p>", unsafe_allow_html=True)
st.sidebar.write("")

pagina_selecionada = st.sidebar.radio(
    "",
    ["🏠 Visão Geral", "📈 Vendas por Mês", "🔄 Comparação de Períodos", "👥 Cliente", "📦 Categoria", "🏭 Fabricante", "🛒 Produto", "📋 Tabela Dinâmica", "⚙️ Configurações"]
)
st.sidebar.divider()

if 'ultima_atualizacao' in st.session_state:
    st.sidebar.caption(f"📅 **Atualizado em:** {st.session_state['ultima_atualizacao']}")
    st.sidebar.caption(f"📁 **Fonte:** google_sheets_sync")
    st.sidebar.caption(f"👤 **User:** {st.session_state['usuario_atual']}")

if st.sidebar.button("🔒 Sair do Painel", use_container_width=True):
    st.session_state["autenticado"] = False
    if "usr" in st.query_params: del st.query_params["usr"]
    st.rerun()

# ==========================================================
# FILTRO EM LINHA ÚNICA NATIVA DENTRO DO CONTAINER
# ==========================================================
with st.container(border=True):
    hoje = date.today()
    primeiro_dia_mes = date(hoje.year, hoje.month, 1)
    min_data_db = df_base['Data'].min().date() if not df_base.empty else date(2020, 1, 1)

    col_preset, col_per_ini, col_per_fim, col_can, col_cat, col_sub, col_fab, col_pro, col_btn = st.columns([1.5, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 0.8])
    with col_preset:
        time_preset = st.selectbox("Período Rápido", options=["Customizado", "Este Mês (MTD)", "Ano Corrente (YTD)", "Últimos 30 Dias", "Todo o Histórico"], index=1)

    if time_preset == "Este Mês (MTD)": data_inicial_calculada, data_final_calculada = primeiro_dia_mes, hoje
    elif time_preset == "Ano Corrente (YTD)": data_inicial_calculada, data_final_calculada = date(hoje.year, 1, 1), hoje
    elif time_preset == "Últimos 30 Dias": data_inicial_calculada, data_final_calculada = hoje - relativedelta(days=30), hoje
    elif time_preset == "Todo o Histórico": data_inicial_calculada, data_final_calculada = min_data_db, hoje
    else: data_inicial_calculada, data_final_calculada = primeiro_dia_mes, hoje

    with col_per_ini: data_inicio = st.date_input("Data Inicial", value=data_inicial_calculada, min_value=min_data_db, max_value=hoje, format="DD/MM/YYYY", disabled=(time_preset != "Customizado"))
    with col_per_fim: data_fim = st.date_input("Data Final", value=data_final_calculada, min_value=min_data_db, max_value=hoje, format="DD/MM/YYYY", disabled=(time_preset != "Customizado"))
        
    with col_can: canais = st.multiselect("Cliente", options=df_base['Cliente'].dropna().unique(), placeholder="Todos")
    with col_cat: categorias = st.multiselect("Categoria", options=df_base['Categoria'].dropna().unique(), placeholder="Todas")
    with col_sub: subcategorias = st.multiselect("Subcategoria", options=df_base['Subcategoria'].dropna().unique(), placeholder="Todas")
    with col_fab: fabricantes = st.multiselect("Fabricante", options=df_base['Fabricante'].dropna().unique(), placeholder="Todos")
    with col_pro: produtos = st.multiselect("Produto", options=df_base['Produto'].dropna().unique(), placeholder="Todos")
    with col_btn:
        st.write(""); st.write("")
        if st.button("🔄 Limpar", use_container_width=True): st.rerun()

inicio_ts, fim_ts = pd.to_datetime(data_inicio), pd.to_datetime(data_fim)
df_filtrado_geral = df_base.copy()
if canais: df_filtrado_geral = df_filtrado_geral[df_filtrado_geral['Cliente'].isin(canais)]
if categorias: df_filtrado_geral = df_filtrado_geral[df_filtrado_geral['Categoria'].isin(categorias)]
if subcategorias: df_filtrado_geral = df_filtrado_geral[df_filtrado_geral['Subcategoria'].isin(subcategorias)]
if fabricantes: df_filtrado_geral = df_filtrado_geral[df_filtrado_geral['Fabricante'].isin(fabricantes)]
if produtos: df_filtrado_geral = df_filtrado_geral[df_filtrado_geral['Produto'].isin(produtos)]

df_atual = df_filtrado_geral[(df_filtrado_geral['Data'] >= inicio_ts) & (df_filtrado_geral['Data'] <= fim_ts)]
df_ly = df_filtrado_geral[(df_filtrado_geral['Data'] >= (inicio_ts - relativedelta(years=1))) & (df_filtrado_geral['Data'] <= (fim_ts - relativedelta(years=1)))]

dias_selecionados = (fim_ts - inicio_ts).days

# Mapeamento e Agregações Compartilhadas
fat_at, qtd_at = df_atual['Total'].sum(), df_atual['Quantidade'].sum()
tk_at = fat_at / qtd_at if qtd_at > 0 else 0
ped_at = df_atual['Ped_Cliente'].nunique()

fat_ly, qtd_ly = df_ly['Total'].sum(), df_ly['Quantidade'].sum()
tk_ly = fat_ly / qtd_ly if qtd_ly > 0 else 0
ped_ly = df_ly['Ped_Cliente'].nunique()

v_fat = ((fat_at / fat_ly) - 1) * 100 if fat_ly > 0 else 0
v_qtd = ((qtd_at / qtd_ly) - 1) * 100 if qtd_ly > 0 else 0
v_tk = ((tk_at / tk_ly) - 1) * 100 if tk_ly > 0 else 0
v_ped = ((ped_at / ped_ly) - 1) * 100 if ped_ly > 0 else 0

fat_at_str = formatar_moeda_br(fat_at)
qtd_at_str = f"{qtd_at:.0f}"
tk_at_str = formatar_moeda_br_completo(tk_at)
ped_at_str = f"{ped_at:.0f}"

v_fat_str = f"{v_fat:+.1f}%".replace('.', ',')
v_qtd_str = f"{v_qtd:+.1f}%".replace('.', ',')
v_tk_str = f"{v_tk:+.1f}%".replace('.', ',')
v_ped_str = f"{v_ped:+.1f}%".replace('.', ',')

# ==========================================================
# 2. ROTEAMENTO EXCLUSIVO DE CONTEÚDO DE TELAS
# ==========================================================
if pagina_selecionada == "🏠 Visão Geral":
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f"<div class='kpi-card blue-accent'><div class='kpi-title'>Qtd de Itens</div><div class='kpi-value'>{qtd_at_str}</div><div class='kpi-footer'><span class='{'badge-positive' if v_qtd >= 0 else 'badge-negative'}'>{v_qtd_str}</span><span class='kpi-ly-text'>vs LY ({f'{qtd_ly:.0f}'})</span></div></div>", unsafe_allow_html=True)
    with k2: st.markdown(f"<div class='kpi-card emerald-accent'><div class='kpi-title'>Ticket Médio</div><div class='kpi-value'>{tk_at_str}</div><div class='kpi-footer'><span class='{'badge-positive' if v_tk >= 0 else 'badge-negative'}'>{v_tk_str}</span><span class='kpi-ly-text'>vs LY ({formatar_moeda_br(tk_ly)})</span></div></div>", unsafe_allow_html=True)
    with k3: st.markdown(f"<div class='kpi-card orange-accent'><div class='kpi-title'>Pedidos</div><div class='kpi-value'>{ped_at_str}</div><div class='kpi-footer'><span class='{'badge-positive' if v_ped >= 0 else 'badge-negative'}'>{v_ped_str}</span><span class='kpi-ly-text'>vs LY ({f'{ped_ly:.0f}'})</span></div></div>", unsafe_allow_html=True)
    with k4: st.markdown(f"<div class='kpi-card purple-accent'><div class='kpi-title'>Vendas</div><div class='kpi-value'>{fat_at_str}</div><div class='kpi-footer'><span class='{'badge-positive' if v_fat >= 0 else 'badge-negative'}'>{v_fat_str}</span><span class='kpi-ly-text'>vs LY ({formatar_moeda_br(fat_ly)})</span></div></div>", unsafe_allow_html=True)
    st.write("\n")

    with st.container(border=True):
        titulo_grafico_tempo = "Faturamento Diário Comercial" if dias_selecionados <= 60 else "Performance Histórica Mensal"
        st.markdown(f"<div class='chart-header'><div class='chart-icon-box'>📈</div><h4 class='chart-title-text'>{titulo_grafico_tempo} (Atual vs LY)</h4></div>", unsafe_allow_html=True)
        
        df_g_atual = pd.DataFrame(columns=['Eixo_X', 'Atual', 'Sort_Key'])
        if not df_atual.empty:
            df_t_atual = df_atual.copy()
            if dias_selecionados <= 60:
                df_t_atual['Sort_Key'] = df_t_atual['Data'].dt.strftime('%Y-%m-%d')
                df_t_atual['Eixo_X'] = df_t_atual['Data'].dt.strftime('%d/%m')
            else:
                df_t_atual['Sort_Key'] = df_t_atual['Data'].dt.strftime('%Y-%m')
                df_t_atual['Eixo_X'] = df_t_atual['Data'].apply(lambda r: f"{meses_pt[r.month]} - {r.strftime('%y')}")
            df_g_atual = df_t_atual.groupby(['Sort_Key', 'Eixo_X'])['Total'].sum().reset_index().rename(columns={'Total': 'Atual'})
            
        df_g_ly = pd.DataFrame(columns=['Eixo_X', 'LY', 'Sort_Key'])
        if not df_ly.empty:
            df_t_ly = df_ly.copy()
            df_t_ly['Data_Shifted'] = df_t_ly['Data'].apply(lambda x: x + relativedelta(years=1))
            if dias_selecionados <= 60:
                df_t_ly['Sort_Key'] = df_t_ly['Data_Shifted'].dt.strftime('%Y-%m-%d')
                df_t_ly['Eixo_X'] = df_t_ly['Data_Shifted'].dt.strftime('%d/%m')
            else:
                df_t_ly['Sort_Key'] = df_t_ly['Data_Shifted'].dt.strftime('%Y-%m')
                df_t_ly['Eixo_X'] = df_t_ly['Data_Shifted'].apply(lambda r: f"{meses_pt[r.month]} - {r.strftime('%y')}")
            df_g_ly = df_t_ly.groupby(['Sort_Key', 'Eixo_X'])['Total'].sum().reset_index().rename(columns={'Total': 'LY'})

        if not df_g_atual.empty or not df_g_ly.empty:
            df_graf_temp = pd.merge(df_g_atual, df_g_ly, on=['Sort_Key', 'Eixo_X'], how='outer').fillna(0)
            df_graf_temp = df_graf_temp.sort_values('Sort_Key', ascending=True)
            
            df_graf_temp['Var_Perc'] = df_graf_temp.apply(lambda r: ((r['Atual'] / r['LY']) - 1) * 100 if r['LY'] > 0 else (100 if r['Atual'] > 0 else 0), axis=1)
            df_graf_temp['Texto_Atual'] = df_graf_temp['Atual'].apply(formatar_moeda_br)
            df_graf_temp['Texto_LY'] = df_graf_temp['LY'].apply(formatar_moeda_br)
            df_graf_temp['Texto_Var'] = df_graf_temp['Var_Perc'].apply(lambda x: f"{x:+.1f}%".replace('.', ','))
            df_graf_temp['Hover_Atual'] = df_graf_temp['Atual'].apply(formatar_moeda_br_completo)
            df_graf_temp['Hover_LY'] = df_graf_temp['LY'].apply(formatar_moeda_br_completo)
            
            lista_anotacoes = []
            max_global_val = max(df_graf_temp['Atual'].max(), df_graf_temp['LY'].max())
            
            if dias_selecionados <= 60:
                fig_mes = go.Figure()
                fig_mes.add_trace(go.Scatter(x=df_graf_temp['Eixo_X'], y=df_graf_temp['LY'], name='Ano Anterior (LY)', mode='lines+markers', line=dict(color='#F59E0B', width=2, shape='spline'), fill='tozeroy', fillcolor='rgba(245, 158, 11, 0.02)', marker=dict(color='#F59E0B', size=4), customdata=df_graf_temp['Hover_LY'], hovertemplate="<b>LY:</b> %{customdata}<extra></extra>"))
                fig_mes.add_trace(go.Scatter(x=df_graf_temp['Eixo_X'], y=df_graf_temp['Atual'], name='Ano Atual', mode='lines+markers', line=dict(color='#3B82F6', width=2.5, shape='spline'), fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.08)', marker=dict(color='#3B82F6', size=5), customdata=df_graf_temp[['Hover_Atual', 'Texto_Var']], hovertemplate="<b>Atual:</b> %{customdata[0]}<br><b>Cresc. vs LY:</b> %{customdata[1]}<extra></extra>"))
                
                for i, row in df_graf_temp.iterrows():
                    if row['LY'] > 0: lista_anotacoes.append(dict(x=row['Eixo_X'], y=row['LY'], text=row['Texto_LY'], showarrow=False, yshift=-14, font=dict(color='white', size=11, family='Inter', weight='bold'), bgcolor='#F59E0B', borderpad=2.5, xanchor='center'))
                    if row['Atual'] > 0: lista_anotacoes.append(dict(x=row['Eixo_X'], y=row['Atual'], text=row['Texto_Atual'], showarrow=False, yshift=14, font=dict(color='white', size=11, family='Inter', weight='bold'), bgcolor='#3B82F6', borderpad=2.5, xanchor='center'))
            else:
                fig_mes = make_subplots(specs=[[{"secondary_y": True}]])
                x_indices = list(range(len(df_graf_temp)))
                fig_mes.add_trace(go.Bar(x=x_indices, y=df_graf_temp['Atual'], name='Ano Atual', marker_color='#3B82F6', customdata=df_graf_temp['Hover_Atual'], hovertemplate="<b>Atual:</b> %{customdata}<extra></extra>"), secondary_y=False)
                fig_mes.add_trace(go.Bar(x=x_indices, y=df_graf_temp['LY'], name='Ano Anterior (LY)', marker_color='#F59E0B', customdata=df_graf_temp['Hover_LY'], hovertemplate="<b>LY:</b> %{customdata}<extra></extra>"), secondary_y=False)
                fig_mes.add_trace(go.Scatter(x=x_indices, y=df_graf_temp['Var_Perc'], name='Crescimento %', mode='lines+markers', line=dict(color='#64748B', width=2), marker=dict(size=5), customdata=df_graf_temp['Texto_Var'], hovertemplate="<b>Cresc:</b> %{customdata}<extra></extra>"), secondary_y=True)
                
                for i, row in df_graf_temp.iterrows():
                    if row['LY'] > 0: lista_anotacoes.append(dict(x=i + 0.20, y=row['LY'], text=row['Texto_LY'], showarrow=False, yshift=6, xanchor='center', yanchor='bottom', font=dict(color='white', size=11, family='Inter', weight='bold'), bgcolor='#F59E0B', borderpad=3))
                    if row['Atual'] > 0: lista_anotacoes.append(dict(x=i - 0.20, y=row['Atual'], text=row['Texto_Atual'], showarrow=False, yshift=6, xanchor='center', yanchor='bottom', font=dict(color='white', size=11, family='Inter', weight='bold'), bgcolor='#3B82F6', borderpad=3))
                    lista_anotacoes.append(dict(x=i, y=row['Var_Perc'], text=row['Texto_Var'], showarrow=False, yshift=16, xanchor='center', yanchor='bottom', font=dict(color='white', size=11, family='Inter', weight='bold'), bgcolor='#1E293B', borderpad=3.5, xref="x", yref="y2"))
                
                fig_mes.update_layout(xaxis=dict(title="", showgrid=False, tickmode='array', tickvals=x_indices, ticktext=df_graf_temp['Eixo_X']), yaxis=dict(range=[0, max_global_val * 1.30]))
            
            fig_mes.update_layout(plot_bgcolor='#0E1320', paper_bgcolor='#0E1320', font=dict(color='#94A3B8', size=11), yaxis=dict(title="", showgrid=False, showticklabels=False), yaxis2=dict(title="", showgrid=False, showticklabels=False) if dias_selecionados > 60 else None, margin=dict(l=15, r=15, t=15, b=40), hovermode='x unified', legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(color='#94A3B8', size=11)), annotations=lista_anotacoes, height=420)
            st.plotly_chart(fig_mes, use_container_width=True, config={'displayModeBar': 'hover'})

    col_bottom1, col_bottom2 = st.columns(2)
    with col_bottom1:
        with st.container(border=True):
            st.markdown(f"<div class='chart-header'><div class='chart-icon-box'>📊</div><h4 class='chart-title-text'>Faturamento por Cliente</h4></div>", unsafe_allow_html=True)
            if not df_atual.empty and df_atual['Total'].sum() > 0:
                df_graf_cliente = df_atual.groupby('Cliente')['Total'].sum().reset_index().sort_values(by='Total', ascending=True)
                df_graf_cliente['Texto_Total'] = df_graf_cliente['Total'].apply(formatar_moeda_br)
                fig_cliente = px.bar(df_graf_cliente, x='Total', y='Cliente', orientation='h', color='Total', color_continuous_scale=['#EA580C', '#2563EB'])
                for idx, row in df_graf_cliente.iterrows():
                    fig_cliente.add_annotation(dict(x=row['Total'], y=row['Cliente'], text=row['Texto_Total'], showarrow=False, xshift=8, font=dict(color='#F8FAFC', size=11, family='Inter', weight='bold'), yanchor='middle', xanchor='left'))
                fig_cliente.update_layout(plot_bgcolor='#0E1320', paper_bgcolor='#0E1320', font_color='#94A3B8', xaxis=dict(title="", showgrid=False, showticklabels=False), yaxis=dict(title="", showgrid=False), margin=dict(l=15, r=15, t=10, b=40), coloraxis_showscale=False, height=350, legend=dict(orientation="h", xanchor="center", x=0.5, y=-0.25))
                st.plotly_chart(fig_cliente, use_container_width=True, config={'displayModeBar': 'hover'})

    with col_bottom2:
        with st.container(border=True):
            st.markdown(f"<div class='chart-header'><div class='chart-icon-box'>📦</div><h4 class='chart-title-text'>Vendas por Categoria</h4></div>", unsafe_allow_html=True)
            if not df_atual.empty and df_atual['Total'].sum() > 0:
                df_graf_cat = df_atual.groupby('Categoria')['Total'].sum().reset_index().sort_values(by='Total', ascending=False)
                fig_cat = px.bar(df_graf_cat, x='Categoria', y='Total', color='Total', color_continuous_scale=['#EA580C', '#2563EB'])
                for idx, row in df_graf_cat.iterrows():
                    fig_cat.add_annotation(dict(x=row['Categoria'], y=row['Total'], text=formatar_moeda_br(row['Total']), showarrow=False, yshift=6, font=dict(color='#F8FAFC', size=11, family='Inter', weight='bold'), yanchor='bottom', xanchor='center'))
                fig_cat.update_layout(plot_bgcolor='#0E1320', paper_bgcolor='#0E1320', font_color='#94A3B8', xaxis=dict(title="", showgrid=False), yaxis=dict(title="", showgrid=False, showticklabels=False, range=[0, df_graf_cat['Total'].max() * 1.25]), margin=dict(l=15, r=15, t=10, b=40), coloraxis_showscale=False, height=350, legend=dict(orientation="h", xanchor="center", x=0.5, y=-0.25))
                st.plotly_chart(fig_cat, use_container_width=True, config={'displayModeBar': 'hover'})

    with st.container(border=True):
        st.markdown(f"<div class='chart-header'><div class='chart-icon-box'>🏭</div><h4 class='chart-title-text'>Faturamento por Fabricante</h4></div>", unsafe_allow_html=True)
        if not df_atual.empty and df_atual['Total'].sum() > 0:
            df_graf_fab = df_atual.groupby('Fabricante')['Total'].sum().reset_index().sort_values(by='Total', ascending=True)
            df_graf_fab['Texto_Total'] = df_graf_fab['Total'].apply(formatar_moeda_br)
            fig_fab = px.bar(df_graf_fab, x='Total', y='Fabricante', orientation='h', color='Total', color_continuous_scale=['#EA580C', '#2563EB'])
            for idx, row in df_graf_fab.iterrows():
                fig_fab.add_annotation(dict(x=row['Total'], y=row['Fabricante'], text=row['Texto_Total'], showarrow=False, xshift=8, font=dict(color='#F8FAFC', size=11, family='Inter', weight='bold'), yanchor='middle', xanchor='left'))
            fig_fab.update_layout(plot_bgcolor='#0E1320', paper_bgcolor='#0E1320', font_color='#94A3B8', xaxis=dict(title="", showgrid=False, showticklabels=False), yaxis=dict(title="", showgrid=False), margin=dict(l=15, r=15, t=10, b=40), coloraxis_showscale=False, height=420, legend=dict(orientation="h", xanchor="center", x=0.5, y=-0.25))
            st.plotly_chart(fig_fab, use_container_width=True, config={'displayModeBar': 'hover'})

# ==========================================================
# 📈 ABA: VENDAS POR MÊS (PROMOVIDA A DASHBOARD DE SAZONALIDADE)
# ==========================================================
elif pagina_selecionada == "📈 Vendas por Mês":
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f"<div class='kpi-card blue-accent'><div class='kpi-title'>Qtd de Itens</div><div class='kpi-value'>{qtd_at_str}</div><div class='kpi-footer'><span class='{'badge-positive' if v_qtd >= 0 else 'badge-negative'}'>{v_qtd_str}</span><span class='kpi-ly-text'>vs LY ({f'{qtd_ly:.0f}'})</span></div></div>", unsafe_allow_html=True)
    with k2: st.markdown(f"<div class='kpi-card emerald-accent'><div class='kpi-title'>Ticket Médio</div><div class='kpi-value'>{tk_at_str}</div><div class='kpi-footer'><span class='{'badge-positive' if v_tk >= 0 else 'badge-negative'}'>{v_tk_str}</span><span class='kpi-ly-text'>vs LY ({formatar_moeda_br(tk_ly)})</span></div></div>", unsafe_allow_html=True)
    with k3: st.markdown(f"<div class='kpi-card orange-accent'><div class='kpi-title'>Pedidos</div><div class='kpi-value'>{ped_at_str}</div><div class='kpi-footer'><span class='{'badge-positive' if v_ped >= 0 else 'badge-negative'}'>{v_ped_str}</span><span class='kpi-ly-text'>vs LY ({f'{ped_ly:.0f}'})</span></div></div>", unsafe_allow_html=True)
    with k4: st.markdown(f"<div class='kpi-card purple-accent'><div class='kpi-title'>Vendas</div><div class='kpi-value'>{fat_at_str}</div><div class='kpi-footer'><span class='{'badge-positive' if v_fat >= 0 else 'badge-negative'}'>{v_fat_str}</span><span class='kpi-ly-text'>vs LY ({formatar_moeda_br(fat_ly)})</span></div></div>", unsafe_allow_html=True)
    st.write("\n")

    with st.container(border=True):
        st.markdown(f"<div class='chart-header'><div class='chart-icon-box'>📈</div><h4 class='chart-title-text'>Histórico Comercial Mensal Estruturado</h4></div>", unsafe_allow_html=True)
        if not df_atual.empty and df_atual['Total'].sum() > 0:
            
            df_matriz_mes = gerar_tabela_analitica_padrao(df_atual, df_ly, 'Mes_Ano', incluir_total=True)
            df_graf_mes = df_matriz_mes[df_matriz_mes['Mes_Ano'] != "Total Geral"].copy()
            
            if not df_graf_mes.empty:
                fig_vendas_mes = make_subplots(specs=[[{"secondary_y": True}]])
                x_indices = list(range(len(df_graf_mes)))
                
                fig_vendas_mes.add_trace(go.Bar(x=x_indices, y=df_graf_mes['Vendas'], name='Ano Atual', marker_color='#3B82F6', customdata=df_graf_mes['Vendas'].apply(formatar_moeda_br_completo), hovertemplate="<b>Atual:</b> %{customdata}<extra></extra>"), secondary_y=False)
                fig_vendas_mes.add_trace(go.Bar(x=x_indices, y=df_graf_mes['Vendas LY'], name='Ano Anterior (LY)', marker_color='#F59E0B', customdata=df_graf_mes['Vendas LY'].apply(formatar_moeda_br_completo), hovertemplate="<b>LY:</b> %{customdata}<extra></extra>"), secondary_y=False)
                fig_vendas_mes.add_trace(go.Scatter(x=x_indices, y=df_graf_mes['Diferença Vendas %'], name='Diferença %', mode='lines+markers', line=dict(color='#64748B', width=2), marker=dict(size=6), customdata=df_graf_mes['Diferença Vendas %'].apply(lambda x: f"{x:+.1f}%".replace('.', ',')), hovertemplate="<b>Cresc:</b> %{customdata}<extra></extra>"), secondary_y=True)
                
                lista_anotacoes_mes = []
                for idx, row_g in df_graf_mes.iterrows():
                    i = df_graf_mes.index.get_loc(idx)
                    if row_g['Vendas LY'] > 0:
                        lista_anotacoes_mes.append(dict(x=i + 0.20, y=row_g['Vendas LY'], text=formatar_moeda_br(row_g['Vendas LY']), showarrow=False, yshift=6, xanchor='center', yanchor='bottom', font=dict(color='white', size=10, family='Inter', weight='bold'), bgcolor='#F59E0B', borderpad=2))
                    if row_g['Vendas'] > 0:
                        lista_anotacoes_mes.append(dict(x=i - 0.20, y=row_g['Vendas'], text=formatar_moeda_br(row_g['Vendas']), showarrow=False, yshift=6, xanchor='center', yanchor='bottom', font=dict(color='white', size=10, family='Inter', weight='bold'), bgcolor='#3B82F6', borderpad=2))
                    lista_anotacoes_mes.append(dict(x=i, y=row_g['Diferença Vendas %'], text=f"{row_g['Diferença Vendas %']:+.1f}%".replace('.', ','), showarrow=False, yshift=14, xanchor='center', yanchor='bottom', font=dict(color='white', size=10, family='Inter', weight='bold'), bgcolor='#1E293B', borderpad=3, xref="x", yref="y2"))
                
                max_val_mes = max(df_graf_mes['Vendas'].max(), df_graf_mes['Vendas LY'].max()) if not df_graf_mes.empty else 1
                fig_vendas_mes.update_layout(plot_bgcolor='#0E1320', paper_bgcolor='#0E1320', font=dict(color='#94A3B8', size=11), xaxis=dict(title="", showgrid=False, tickmode='array', tickvals=x_indices, ticktext=df_graf_mes['Mes_Ano']), yaxis=dict(title="", showgrid=False, showticklabels=False, range=[0, max_val_mes * 1.25]), yaxis2=dict(title="", showgrid=False, showticklabels=False), margin=dict(l=15, r=15, t=20, b=40), barmode='group', legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5), annotations=lista_anotacoes_mes, height=420)
                st.plotly_chart(fig_vendas_mes, use_container_width=True, config={'displayModeBar': 'hover'})
            
            st.dataframe(df_matriz_mes, use_container_width=True, hide_index=True, column_config=obter_config_colunas_bi(df_matriz_mes, "Mês / Ano"))

# ==========================================================
# 🔄 COMPARAÇÃO DE PERÍODOS (DATA A VS DATA B REAL COM CALENDÁRIO CORPORATIVO SEPARADO)
# ==========================================================
elif pagina_selecionada == "🔄 Comparação de Períodos":
    with st.container(border=True):
        c_b_title = st.markdown("<p style='margin:0 0 10px 0; font-weight:600; color:#94A3B8;'>Configurar Período B para Comparação Dinâmica</p>", unsafe_allow_html=True)
        c_b_opt, c_b1, c_b2 = st.columns([2, 2, 2])
        with c_b_opt:
            opcao_b = st.selectbox("Comparar Período A com:", ["Ano Anterior (Mesmo período em LY)", "Mês Anterior", "Período Customizado"])
        
        dias_per_a = (pd.to_datetime(data_fim) - pd.to_datetime(data_inicio)).days
        
        if opcao_b == "Ano Anterior (Mesmo período em LY)":
            data_b_ini_calc = data_inicio - relativedelta(years=1)
            data_b_fim_calc = data_fim - relativedelta(years=1)
        elif opcao_b == "Mês Anterior":
            data_b_ini_calc = data_inicio - relativedelta(months=1)
            data_b_fim_calc = data_b_ini_calc + timedelta(days=dias_per_a)
        else:
            data_b_ini_calc = data_inicio - relativedelta(months=1)
            data_b_fim_calc = data_b_ini_calc + timedelta(days=dias_per_a)

        with c_b1: data_b_ini = st.date_input("Período B - Início", value=data_b_ini_calc, format="DD/MM/YYYY", disabled=(opcao_b != "Período Customizado"))
        with c_b2: data_b_fim = st.date_input("Período B - Fim", value=data_b_fim_calc, format="DD/MM/YYYY", disabled=(opcao_b != "Período Customizado"))
            
    ini_a_ts, fim_a_ts = pd.to_datetime(data_inicio), pd.to_datetime(data_fim)
    ini_b_ts, fim_b_ts = pd.to_datetime(data_b_ini), pd.to_datetime(data_b_fim)
    
    df_per_a = df_filtrado_geral[(df_filtrado_geral['Data'] >= ini_a_ts) & (df_filtrado_geral['Data'] <= fim_a_ts)]
    df_per_b = df_filtrado_geral[(df_filtrado_geral['Data'] >= ini_b_ts) & (df_filtrado_geral['Data'] <= fim_b_ts)]
    
    fat_a, qtd_a = df_per_a['Total'].sum(), df_per_a['Quantidade'].sum()
    tk_a = fat_a / qtd_a if qtd_a > 0 else 0
    ped_a = df_per_a['Ped_Cliente'].nunique()

    fat_b, qtd_b = df_per_b['Total'].sum(), df_per_b['Quantidade'].sum()
    tk_b = fat_b / qtd_b if qtd_b > 0 else 0
    ped_b = df_per_b['Ped_Cliente'].nunique()

    v_fat_c = ((fat_a / fat_b) - 1) * 100 if fat_b > 0 else 0
    v_qtd_c = ((qtd_a / qtd_b) - 1) * 100 if qtd_b > 0 else 0
    v_tk_c = ((tk_a / tk_b) - 1) * 100 if tk_b > 0 else 0
    v_ped_c = ((ped_a / ped_b) - 1) * 100 if ped_b > 0 else 0
    
    # 🎯 BUGFIX DECLARADO: Variável injetada antes de renderizar os cards e st.markdown para evitar NameError
    titulo_grafico_tempo = "Faturamento Diário Comercial" if dias_per_a <= 60 else "Performance Histórica Mensal"
    
    kc1, kc2, kc3, kc4 = st.columns(4)
    with kc1: st.markdown(f"<div class='kpi-card blue-accent'><div class='kpi-title'>Qtd de Itens (Período A)</div><div class='kpi-value'>{qtd_a:.0f}</div><div class='kpi-footer'><span class='{'badge-positive' if v_qtd_c >= 0 else 'badge-negative'}'>{v_qtd_c:+.1f}%</span><span class='kpi-ly-text'>vs Período B ({qtd_b:.0f})</span></div></div>", unsafe_allow_html=True)
    with kc2: st.markdown(f"<div class='kpi-card emerald-accent'><div class='kpi-title'>Ticket Médio (Período A)</div><div class='kpi-value'>{formatar_moeda_br_completo(tk_a)}</div><div class='kpi-footer'><span class='{'badge-positive' if v_tk_c >= 0 else 'badge-negative'}'>{v_tk_c:+.1f}%</span><span class='kpi-ly-text'>vs Período B ({formatar_moeda_br(tk_b)})</span></div></div>", unsafe_allow_html=True)
    with kc3: st.markdown(f"<div class='kpi-card orange-accent'><div class='kpi-title'>Pedidos (Período A)</div><div class='kpi-value'>{ped_a:.0f}</div><div class='kpi-footer'><span class='{'badge-positive' if v_ped_c >= 0 else 'badge-negative'}'>{v_ped_c:+.1f}%</span><span class='kpi-ly-text'>vs Período B ({ped_b:.0f})</span></div></div>", unsafe_allow_html=True)
    with kc4: st.markdown(f"<div class='kpi-card purple-accent'><div class='kpi-title'>Vendas (Período A)</div><div class='kpi-value'>{formatar_moeda_br(fat_a)}</div><div class='kpi-footer'><span class='{'badge-positive' if v_fat_c >= 0 else 'badge-negative'}'>{v_fat_c:+.1f}%</span><span class='kpi-ly-text'>vs Período B ({formatar_moeda_br(fat_b)})</span></div></div>", unsafe_allow_html=True)
    st.write("\n")

    # ==========================================================
    # 🎯 MOTOR RECALIBRADO: EXIBE AS DATAS E MESES REAIS NO EIXO X DO GRÁFICO
    # ==========================================================
    if dias_per_a <= 60:
        df_g_a = df_per_a.groupby(df_per_a['Data'].dt.normalize())['Total'].sum().reset_index().sort_values('Data')
        df_g_a['Idx'] = range(len(df_g_a))
        df_g_b = df_per_b.groupby(df_per_b['Data'].dt.normalize())['Total'].sum().reset_index().sort_values('Data')
        df_g_b['Idx'] = range(len(df_g_b))
        
        df_graf_comp = pd.merge(df_g_a, df_g_b, on='Idx', how='outer', suffixes=('_A', '_B')).fillna(0)
        df_graf_comp['Eixo_X'] = df_graf_comp.apply(
            lambda r: f"{pd.to_datetime(r['Data_A']).strftime('%d/%m') if r['Data_A'] != 0 else ''} vs {pd.to_datetime(r['Data_B']).strftime('%d/%m') if r['Data_B'] != 0 else ''}", axis=1
        )
        df_graf_comp['Var_Perc'] = df_graf_comp.apply(lambda r: ((r['Total_A'] / r['Total_B']) - 1) * 100 if r['Total_B'] > 0 else (100 if r['Total_A'] > 0 else 0), axis=1)
        df_graf_comp['Texto_Atual'] = df_graf_comp['Total_A'].apply(formatar_moeda_br)
        df_graf_comp['Texto_LY'] = df_graf_comp['Total_B'].apply(formatar_moeda_br)
        df_graf_comp['Texto_Var'] = df_graf_comp['Var_Perc'].apply(lambda x: f"{x:+.1f}%".replace('.', ','))
        df_graf_comp['Hover_Atual'] = df_graf_comp['Total_A'].apply(formatar_moeda_br_completo)
        df_graf_comp['Hover_LY'] = df_graf_comp['Total_B'].apply(formatar_moeda_br_completo)

        with st.container(border=True):
            st.markdown(f"<div class='chart-header'><div class='chart-icon-box'>📈</div><h4 class='chart-title-text'>{titulo_grafico_tempo} (Período A vs Período B)</h4></div>", unsafe_allow_html=True)
            
            lista_anotacoes_comp = []
            fig_comp_dates = go.Figure()
            fig_comp_dates.add_trace(go.Scatter(x=df_graf_comp['Eixo_X'], y=df_graf_comp['Total_B'], name='Período B', mode='lines+markers', line=dict(color='#F59E0B', width=2, shape='spline'), fill='tozeroy', fillcolor='rgba(245, 158, 11, 0.02)', marker=dict(color='#F59E0B', size=4), customdata=df_graf_comp['Hover_LY'], hovertemplate="<b>Período B:</b> %{customdata}<extra></extra>"))
            fig_comp_dates.add_trace(go.Scatter(x=df_graf_comp['Eixo_X'], y=df_graf_comp['Total_A'], name='Período A', mode='lines+markers', line=dict(color='#3B82F6', width=2.5, shape='spline'), fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.08)', marker=dict(color='#3B82F6', size=5), customdata=df_graf_comp[['Hover_Atual', 'Texto_Var']], hovertemplate="<b>Período A:</b> %{customdata[0]}<br><b>Var:</b> %{customdata[1]}<extra></extra>"))
            
            if len(df_graf_comp) <= 31:
                for i, row in df_graf_comp.iterrows():
                    if row['Total_B'] > 0: lista_anotacoes_comp.append(dict(x=row['Eixo_X'], y=row['Total_B'], text=row['Texto_LY'], showarrow=False, yshift=-14, font=dict(color='white', size=11, family='Inter', weight='bold'), bgcolor='#F59E0B', borderpad=2.5, xanchor='center'))
                    if row['Total_A'] > 0: lista_anotacoes_comp.append(dict(x=row='Eixo_X'], y=row['Total_A'], text=row['Texto_Atual'], showarrow=False, yshift=14, font=dict(color='white', size=11, family='Inter', weight='bold'), bgcolor='#3B82F6', borderpad=2.5, xanchor='center'))
            
            fig_comp_dates.update_layout(plot_bgcolor='#0E1320', paper_bgcolor='#0E1320', font=dict(color='#94A3B8', size=11), yaxis=dict(title="", showgrid=False, showticklabels=False), margin=dict(l=15, r=15, t=15, b=40), hovermode='x unified', legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(color='#94A3B8', size=11)), annotations=lista_anotacoes_comp, height=420)
            st.plotly_chart(fig_comp_dates, use_container_width=True, config={'displayModeBar': 'hover'})
    else:
        df_g_a = df_per_a.groupby(df_per_a['Data'].dt.to_period('M'))['Total'].sum().reset_index().sort_values('Data')
        df_g_a['Idx'] = range(len(df_g_a))
        df_g_b = df_per_b.groupby(df_per_b['Data'].dt.to_period('M'))['Total'].sum().reset_index().sort_values('Data')
        df_g_b['Idx'] = range(len(df_g_b))
        
        df_graf_comp = pd.merge(df_g_a, df_g_b, on='Idx', how='outer', suffixes=('_A', '_B')).fillna(0)
        
        def format_p_extenso(val):
            if val == 0: return ""
            return f"{meses_pt[val.month]} - {str(val.year)[2:]}"
            
        df_graf_comp['Eixo_X'] = df_graf_comp.apply(
            lambda r: f"{format_p_extenso(r['Data_A'])} vs {format_p_extenso(r['Data_B'])}", axis=1
        )
        df_graf_comp['Var_Perc'] = df_graf_comp.apply(lambda r: ((r['Total_A'] / r['Total_B']) - 1) * 100 if r['Total_B'] > 0 else (100 if r['Total_A'] > 0 else 0), axis=1)
        df_graf_comp['Texto_Atual'] = df_graf_comp['Total_A'].apply(formatar_moeda_br)
        df_graf_comp['Texto_LY'] = df_graf_comp['Total_B'].apply(formatar_moeda_br)
        df_graf_comp['Texto_Var'] = df_graf_comp['Var_Perc'].apply(lambda x: f"{x:+.1f}%".replace('.', ','))
        df_graf_comp['Hover_Atual'] = df_graf_comp['Total_A'].apply(formatar_moeda_br_completo)
        df_graf_comp['Hover_LY'] = df_graf_comp['Total_B'].apply(formatar_moeda_br_completo)
        
        with st.container(border=True):
            st.markdown(f"<div class='chart-header'><div class='chart-icon-box'>📈</div><h4 class='chart-title-text'>{titulo_grafico_tempo} (Período A vs Período B)</h4></div>", unsafe_allow_html=True)
            
            lista_anotacoes_comp = []
            max_global_val = max(df_graf_comp['Total_A'].max(), df_graf_comp['Total_B'].max()) if not df_graf_comp.empty else 1
            
            fig_comp_dates = make_subplots(specs=[[{"secondary_y": True}]])
            x_indices = list(range(len(df_graf_comp)))
            
            fig_comp_dates.add_trace(go.Bar(x=x_indices, y=df_graf_comp['Total_A'], name='Período A', marker_color='#3B82F6', customdata=df_graf_comp['Hover_Atual'], hovertemplate="<b>Período A:</b> %{customdata}<extra></extra>"), secondary_y=False)
            fig_comp_dates.add_trace(go.Bar(x=x_indices, y=df_graf_comp['Total_B'], name='Período B', marker_color='#F59E0B', customdata=df_graf_comp['Hover_LY'], hovertemplate="<b>Período B:</b> %{customdata}<extra></extra>"), secondary_y=False)
            fig_comp_dates.add_trace(go.Scatter(x=x_indices, y=df_graf_comp['Var_Perc'], name='Variação %', mode='lines+markers', line=dict(color='#64748B', width=2), marker=dict(size=5), customdata=df_graf_comp['Texto_Var'], hovertemplate="<b>Var:</b> %{customdata}<extra></extra>"), secondary_y=True)
            
            for i, row in df_graf_comp.iterrows():
                if row['Total_B'] > 0: lista_anotacoes_comp.append(dict(x=i + 0.20, y=row['Total_B'], text=row['Texto_LY'], showarrow=False, yshift=6, xanchor='center', yanchor='bottom', font=dict(color='white', size=11, family='Inter', weight='bold'), bgcolor='#F59E0B', borderpad=3))
                if row['Total_A'] > 0: lista_anotacoes_comp.append(dict(x=i - 0.20, y=row['Total_A'], text=row['Texto_Atual'], showarrow=False, yshift=6, xanchor='center', yanchor='bottom', font=dict(color='white', size=11, family='Inter', weight='bold'), bgcolor='#3B82F6', borderpad=3))
                lista_anotacoes_comp.append(dict(x=i, y=row['Var_Perc'], text=row['Texto_Var'], showarrow=False, yshift=16, xanchor='center', yanchor='bottom', font=dict(color='white', size=11, family='Inter', weight='bold'), bgcolor='#1E293B', borderpad=3.5, xref="x", yref="y2"))
            
            fig_comp_dates.update_layout(plot_bgcolor='#0E1320', paper_bgcolor='#0E1320', font=dict(color='#94A3B8', size=11), xaxis=dict(title="", showgrid=False, tickmode='array', tickvals=x_indices, ticktext=df_graf_comp['Eixo_X']), yaxis=dict(range=[0, max_global_val * 1.30]), yaxis2=dict(title="", showgrid=False, showticklabels=False), margin=dict(l=15, r=15, t=15, b=40), hovermode='x unified', legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(color='#94A3B8', size=11)), annotations=lista_anotacoes_comp, height=420)
            st.plotly_chart(fig_comp_dates, use_container_width=True, config={'displayModeBar': 'hover'})

    # Tabela Dinâmica Multi-Nível Expandível Adaptada Autônoma com Rótulos A para A e B para B
    with st.container(border=True):
        st.markdown(f"<div class='chart-header'><div class='chart-icon-box'>📋</div><h4 class='chart-title-text'>Matriz Dinâmica Executiva: Período A vs Período B</h4></div>", unsafe_allow_html=True)
        e_linhas_comp = st.selectbox("Selecionar Tabela de Comparação", options=["Cliente", "Categoria", "Subcategoria", "Fabricante"], key="selectbox_comp_periodos_dinamico")
        if not df_per_a.empty or not df_per_b.empty:
            df_matriz_macro = gerar_tabela_analitica_padrao(df_per_a, df_per_b, e_linhas_comp, incluir_total=False).sort_values(by='Vendas', ascending=False)
            linhas_exibicao, mapeamento_linhas, ponteiro_indice = [], {}, 0
            
            for _, row in df_matriz_macro.iterrows():
                item_nome = row[e_linhas_comp]
                esta_expandido = item_nome in st.session_state['expanded_items']
                linha_mestre = row.copy()
                linha_mestre[e_linhas_comp] = f"   -   {item_nome}" if esta_expandido else f"   +   {item_nome}"
                linhas_exibicao.append(linha_mestre)
                mapeamento_linhas[ponteiro_indice] = {'type': 'master', 'name': item_nome}
                ponteiro_indice += 1
                
                if esta_expandido:
                    df_matriz_sub = gerar_tabela_analitica_padrao(df_per_a[df_per_a[e_linhas_comp] == item_nome], df_per_b[df_per_b[e_linhas_comp] == item_nome], 'Produto', incluir_total=False).sort_values(by='Vendas', ascending=False)
                    for _, sub_row in df_matriz_sub.iterrows():
                        linha_filha = sub_row.copy()
                        linha_filha[e_linhas_comp] = f"          {sub_row['Produto']}"
                        
                        local_index = linha_filha.index
                        if 'Produto' in local_index:
                            linha_filha = linha_filha.drop('Produto')
                            
                        linhas_exibicao.append(linha_filha)
                        mapeamento_linhas[ponteiro_indice] = {'type': 'child', 'name': sub_row['Produto']}
                        ponteiro_indice += 1
                        
            df_final_display = pd.DataFrame(linhas_exibicao) if linhas_exibicao else pd.DataFrame(columns=df_matriz_macro.columns)
            if not df_final_display.empty:
                df_total_geral_row = gerar_tabela_analitica_padrao(df_per_a, df_per_b, e_linhas_comp, incluir_total=True).tail(1).copy()
                df_total_geral_row[e_linhas_comp] = "Total Geral"
                df_final_display = pd.concat([df_final_display, df_total_geral_row], ignore_index=True)
            
            max_v_a = float(df_final_display["Vendas"].max()) if "Vendas" in df_final_display.columns and df_final_display["Vendas"].max() > 0 else 1.0
            max_v_b = float(df_final_display["Vendas LY"].max()) if "Vendas LY" in df_final_display.columns and df_final_display["Vendas LY"].max() > 0 else 1.0
            max_p_a = float(df_final_display["Pedidos"].max()) if "Pedidos" in df_final_display.columns and df_final_display["Pedidos"].max() > 0 else 1.0
            max_p_b = float(df_final_display["Pedidos LY"].max()) if "Pedidos LY" in df_final_display.columns and df_final_display["Pedidos LY"].max() > 0 else 1.0
            max_q_a = float(df_final_display["Qtd de Itens"].max()) if "Qtd de Itens" in df_final_display.columns and df_final_display["Qtd de Itens"].max() > 0 else 1.0
            max_q_b = float(df_final_display["Itens LY"].max()) if "Itens LY" in df_final_display.columns and df_final_display["Itens LY"].max() > 0 else 1.0
            max_t_a = float(df_final_display["Ticket Medio"].max()) if "Ticket Medio" in df_final_display.columns and df_final_display["Ticket Medio"].max() > 0 else 1.0
            max_t_b = float(df_final_display["Ticket Medio LY"].max()) if "Ticket Medio LY" in df_final_display.columns and df_final_display["Ticket Medio LY"].max() > 0 else 1.0

            config_custom_per = {
                df_final_display.columns[0]: st.column_config.TextColumn(e_linhas_comp, alignment="left"),
                "Vendas": st.column_config.ProgressColumn("Vendas Período A", format="R$ %,.2f", min_value=0, max_value=max_v_a, color="blue"),
                "Vendas LY": st.column_config.ProgressColumn("Vendas Período B", format="R$ %,.2f", min_value=0, max_value=max_v_b, color="orange"),
                "Diferença Vendas %": st.column_config.NumberColumn("Var Vendas %", format="%,.2f%%"),
                "% de Participação": st.column_config.ProgressColumn("% Part. Período A", format="%,.2f%%", min_value=0, max_value=100, color="blue"),
                "Pedidos": st.column_config.ProgressColumn("Pedidos Período A", format="%d", min_value=0, max_value=max_p_a, color="blue"),
                "Pedidos LY": st.column_config.ProgressColumn("Pedidos Período B", format="%d", min_value=0, max_value=max_p_b, color="orange"),
                "Diferença Pedidos %": st.column_config.NumberColumn("Var Pedidos %", format="%,.2f%%"),
                "Qtd de Itens": st.column_config.ProgressColumn("Qtd Itens Período A", format="%d", min_value=0, max_value=max_q_a, color="blue"),
                "Itens LY": st.column_config.ProgressColumn("Qtd Itens Período B", format="%d", min_value=0, max_value=max_q_b, color="orange"),
                "Diferença Itens %": st.column_config.NumberColumn("Var Itens %", format="%,.2f%%"),
                "Ticket Medio": st.column_config.ProgressColumn("Tkt Médio Período A", format="R$ %,.2f", min_value=0, max_value=max_t_a, color="blue"),
                "Ticket Medio LY": st.column_config.ProgressColumn("Tkt Médio Período B", format="R$ %,.2f", min_value=0, max_value=max_t_b, color="orange"),
                "Diferença Ticket %": st.column_config.NumberColumn("Var Tkt Médio %", format="%,.2f%%"),
            }
            
            selecao = st.dataframe(df_final_display, use_container_width=True, hide_index=True, column_config=config_custom_per, on_select="rerun", selection_mode="single-row", key=f"pivot_comp_dates_{st.session_state['df_key_counter']}")
            rows_selecionadas = selecao.selection.get("rows", []) if selecao else []
            if rows_selecionadas:
                meta_linha = mapeamento_linhas.get(rows_selecionadas[0])
                if meta_linha and meta_linha['type'] == 'master':
                    if meta_linha['name'] in st.session_state['expanded_items']: st.session_state['expanded_items'].remove(meta_linha['name'])
                    else: st.session_state['expanded_items'].add(meta_linha['name'])
                    st.session_state['df_key_counter'] += 1
                    st.rerun()

# ==========================================================
# 📋 TABELA DINÂMICA
# ==========================================================
elif pagina_selecionada == "📋 Tabela Dinâmica":
    with st.container(border=True):
        st.markdown(f"<div class='chart-header'><div class='chart-icon-box'>📋</div><h4 class='chart-title-text'>Tabelas</h4></div>", unsafe_allow_html=True)
        e_linhas = st.selectbox("Selecionar Tabela", options=["Cliente", "Categoria", "Subcategoria", "Fabricante"])
        if not df_atual.empty or not df_ly.empty:
            df_matriz_macro = gerar_tabela_analitica_padrao(df_atual, df_ly, e_linhas, incluir_total=False).sort_values(by='Vendas', ascending=False)
            linhas_exibicao, mapeamento_linhas, pointer_idx = [], {}, 0
            
            for _, row in df_matriz_macro.iterrows():
                item_nome = row[e_linhas]
                esta_expandido = item_nome in st.session_state['expanded_items']
                linha_mestre = row.copy()
                linha_mestre[e_linhas] = f"   -   {item_nome}" if esta_expandido else f"   +   {item_nome}"
                linhas_exibicao.append(linha_mestre)
                mapeamento_linhas[pointer_idx] = {'type': 'master', 'name': item_nome}
                pointer_idx += 1
                
                if esta_expandido:
                    df_matriz_sub = gerar_tabela_analitica_padrao(df_atual[df_atual[e_linhas] == item_nome], df_ly[df_ly[e_linhas] == item_nome], 'Produto', incluir_total=False).sort_values(by='Vendas', ascending=False)
                    for _, sub_row in df_matriz_sub.iterrows():
                        linha_filha = sub_row.copy()
                        linha_filha[e_linhas] = f"          {sub_row['Produto']}"
                        
                        local_index = linha_filha.index
                        if 'Produto' in local_index:
                            linha_filha = local_index.drop('Produto')
                            
                        linhas_exibicao.append(linha_filha)
                        mapeamento_linhas[pointer_idx] = {'type': 'child', 'name': sub_row['Produto']}
                        pointer_idx += 1
                        
            df_final_display = pd.DataFrame(linhas_exibicao) if lines_exibicao := linhas_exibicao else pd.DataFrame(columns=df_matriz_macro.columns)
            if not df_final_display.empty:
                df_total_geral_row = gerar_tabela_analitica_padrao(df_atual, df_ly, e_linhas, incluir_total=True).tail(1).copy()
                df_total_geral_row[e_linhas] = "Total Geral"
                df_final_display = pd.concat([df_final_display, df_total_geral_row], ignore_index=True)
                
            selecao = st.dataframe(df_final_display, use_container_width=True, hide_index=True, column_config=obter_config_colunas_bi(df_final_display, e_linhas), on_select="rerun", selection_mode="single-row", key=f"pivot_{st.session_state['df_key_counter']}")
            rows_selecionadas = selecao.selection.get("rows", []) if selecao else []
            if rows_selecionadas:
                meta_linha = mapeamento_linhas.get(rows_selecionadas[0])
                if meta_linha and meta_linha['type'] == 'master':
                    if meta_linha['name'] in st.session_state['expanded_items']: st.session_state['expanded_items'].remove(meta_linha['name'])
                    else: st.session_state['expanded_items'].add(meta_linha['name'])
                    st.session_state['df_key_counter'] += 1
                    st.rerun()

# ==========================================================
# ⚙️ ABA: CONFIGURAÇÕES
# ==========================================================
elif pagina_selecionada == "⚙️ Configurações":
    with st.container(border=True):
        st.markdown(f"<div class='chart-header'><div class='chart-icon-box'>⚙️</div><h4 class='chart-title-text'>Console de Governança do Sistema</h4></div>", unsafe_allow_html=True)
        st.write("🔧 **Configurações do Engine de Dados**")
        st.caption(f"Conexão do Banco de Dados: Ativa (PostgreSQL Supabase)")
        st.caption(f"Sincronização de Carga Externa: Conectada (Aba: Base_Vendas)")
        if st.button("🗑️ Limpar Cache do Sistema", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache limpo com sucesso!")