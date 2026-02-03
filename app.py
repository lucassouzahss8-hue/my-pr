import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date

# 1. Configuração da Página
st.set_page_config(
    page_title="Precificador", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Estilização CSS Original
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .titulo-planilha { 
        color: #1e3a8a; 
        font-weight: bold; 
        border-bottom: 2px solid #1e3a8a; 
        margin-bottom: 20px; 
        text-align: center;
    }
    .resultado-box { 
        background-color: #262730; 
        padding: 25px; 
        border-radius: 15px; 
        border-left: 10px solid #1e3a8a; 
        box-shadow: 2px 2px 15px rgba(0,0,0,0.3); 
        color: white; 
    }
    .resultado-box h1, .resultado-box h2, .resultado-box p, .resultado-box b { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO BANCO DE DADOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- INICIALIZAÇÃO DO ESTADO ---
if "n_itens" not in st.session_state:
    st.session_state.n_itens = 1
if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

# --- FUNÇÕES DE DADOS ---
def carregar_ingredientes():
    try:
        df = conn.read(worksheet="Ingredientes", ttl=0)
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    
    st.markdown("<h1 class='titulo-planilha'>📊 Precificador</h1>", unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Ajuste de Taxas")
        taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99)
        km_gratis = st.number_input("KM Isentos", value=5)
        valor_por_km = st.number_input("R$ por KM adicional", value=2.0)

    # --- CONFIGURAÇÕES DO PRODUTO (PARTE SUPERIOR) ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1:
        nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod_main")
    with col_p2:
        margem_lucro = st.number_input("Margem de Lucro (%)", value=135)
    with col_p3:
        distancia_km = st.number_input("Distância (km)", value=0.0)
    with col_p4:
        forma_pagamento = st.selectbox("Pagamento", ["Crédito", "PIX"])

    # --- LÓGICA DE INGREDIENTES (PREENCHIMENTO) ---
    st.divider()
    col_esq, col_dir = st.columns([2, 1])
    
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens = st.number_input("Número de itens:", min_value=1, value=st.session_state.n_itens)
        custo_total_ing = 0.0
        
        for i in range(int(n_itens)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                sel_item = st.selectbox(f"Item {i+1}", [""] + df_ing['nome'].tolist(), key=f"ing_{i}")
            with c2:
                q_ing = st.number_input("Qtd", key=f"q_{i}", value=0.0)
            with c3:
                u_ing = st.selectbox("Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")
            
            # Cálculo de custo proporcional
            if sel_item:
                p_base = float(df_ing[df_ing['nome'] == sel_item]['preco'].values[0])
                u_base = str(df_ing[df_ing['nome'] == sel_item]['unidade'].values[0]).lower()
                fator = 1.0
                if u_ing == "g" and u_base == "kg": fator = 1/1000
                elif u_ing == "ml" and u_base == "l": fator = 1/1000
                
                c_parcial = (q_ing * fator) * p_base
                custo_total_ing += c_parcial
                with c4:
                    st.write(f"R$ {c_parcial:.2f}")

    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra (%)", 0, 15, 2)
        perc_despesas = st.slider("Despesas (%)", 0, 100, 30)
        valor_embalagem = st.number_input("Embalagem (R$)", value=0.0)

    # --- CÁLCULOS E BOX DE RESULTADO ---
    v_quebra = custo_total_ing * (perc_quebra / 100)
    v_desp = custo_total_ing * (perc_despesas / 100)
    custo_prod = custo_total_ing + v_quebra + v_desp + valor_embalagem
    preco_sugerido = custo_prod + (custo_prod * (margem_lucro/100))
    
    st.markdown(f"""
        <div class='resultado-box'>
            <p>VALOR SUGERIDO</p>
            <h1>R$ {preco_sugerido:.2f}</h1>
        </div>
    """, unsafe_allow_html=True)

    # --- ABA DE ORÇAMENTO (O LAYOUT QUE VOCÊ PEDIU) ---
    st.divider()
    st.header("📋 Gerador de Orçamento")
    
    # Seleção da Receita (Puxando da planilha)
    item_selecionado = st.selectbox("Selecione a Receita para o Orçamento:", [""] + df_ing['nome'].tolist())

    col_orc1, col_orc2, col_orc3 = st.columns([2, 1, 1])
    with col_orc1:
        prod_nome = st.text_input("Produto", value=item_selecionado)
    with col_orc2:
        # Aqui ele já tenta sugerir o preço base da planilha se encontrar
        p_unit_sugerido = 0.0
        if item_selecionado:
            p_unit_sugerido = float(df_ing[df_ing['nome'] == item_selecionado]['preco'].values[0])
        p_unit = st.number_input("Preço Unitário (R$)", value=p_unit_sugerido)
    with col_orc3:
        qtd_ped = st.number_input("Quantidade", min_value=1, value=1)

    col_orc4, col_orc5, col_orc6 = st.columns([1, 1, 1])
    with col_orc4:
        v_frete = st.number_input("Taxa de Entrega (R$)", value=0.0)
    with col_orc5:
        v_emb_extra = st.number_input("Embalagem Extra (R$)", value=0.0)
    with col_orc6:
        st.write("")
        if st.button("➕ Adicionar Item", use_container_width=True):
            subtotal = (p_unit * qtd_ped) + v_frete + v_emb_extra
            st.session_state.carrinho.append({
                "Produto": prod_nome,
                "Qtd": qtd_ped,
                "Preço Unit.": p_unit,
                "Subtotal": subtotal
            })
            st.rerun()

    # Tabela do Pedido
    if st.session_state.carrinho:
        df_c = pd.DataFrame(st.session_state.carrinho)
        st.table(df_c)
        total_geral = df_c["Subtotal"].sum()
        st.subheader(f"Total: R$ {total_geral:.2f}")
        
        if st.button("Gerar orçamento para whatsapp"):
            texto_zap = f"Olá! Segue orçamento:\n"
            for _, item in df_c.iterrows():
                texto_zap += f"- {item['Produto']} ({item['Qtd']}x): R$ {item['Subtotal']:.2f}\n"
            texto_zap += f"*Total: R$ {total_geral:.2f}*"
            st.code(texto_zap)

if __name__ == "__main__":
    main()
