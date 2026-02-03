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
if "nome_prod" not in st.session_state:
    st.session_state.nome_prod = ""
if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

# --- FUNÇÕES DE DADOS ---
def carregar_ingredientes():
    try:
        df = conn.read(worksheet="Ingredientes", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['nome', 'unidade', 'preco'])
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

def carregar_receitas_nuvem():
    try:
        df = conn.read(worksheet="Receitas", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas_nuvem()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador</h1>", unsafe_allow_html=True)

    # --- SIDEBAR ORIGINAL ---
    with st.sidebar:
        st.header("⚙️ Ajuste de Taxas")
        taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
        st.divider()
        km_gratis = st.number_input("KM Isentos", value=5)
        valor_por_km = st.number_input("R$ por KM adicional", value=2.0, step=0.1)

    # --- CONFIGURAÇÕES DO PRODUTO ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1:
        nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod")
    with col_p2:
        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=135)
    with col_p3:
        distancia_km = st.number_input("Distância (km)", min_value=0.0, value=0.0, step=0.1)
    with col_p4:
        forma_pagamento = st.selectbox("Pagamento", ["Crédito", "PIX"])
        
    st.divider()

    # --- ÁREA DOS INGREDIENTES (CORREÇÃO DO INDEXERROR) ---
    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens_input = st.number_input("Número de itens:", min_value=1, key="n_itens")
        custo_ingredientes_total = 0.0
        
        for i in range(int(n_itens_input)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                lista_nomes = [""] + df_ing['nome'].tolist()
                escolha = st.selectbox(f"Item {i+1}", options=lista_nomes, key=f"nome_{i}")
            
            if escolha: # Só calcula se houver escolha
                dados_item = df_ing[df_ing['nome'] == escolha].iloc[0]
                with c2:
                    qtd_usada = st.number_input(f"Qtd", key=f"qtd_{i}", step=0.01, value=0.0)
                with c3:
                    unid_uso = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")
                
                fator = 1.0
                u_base = str(dados_item['unidade']).lower().strip()
                if unid_uso == "g" and u_base == "kg": fator = 1/1000
                elif unid_uso == "kg" and u_base == "g": fator = 1000
                elif unid_uso == "ml" and u_base == "l": fator = 1/1000
                
                custo_parcial = (float(qtd_usada) * fator) * float(dados_item['preco'])
                custo_ingredientes_total += custo_parcial
                with c4:
                    st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra (%)", 0, 15, 2)
        perc_despesas = st.slider("Despesas Gerais (%)", 0, 100, 30)
        valor_embalagem = st.number_input("Embalagem (R$)", min_value=0.0, value=0.0)

    # --- CÁLCULOS FINAIS ---
    taxa_entrega_base = (distancia_km - km_gratis) * valor_por_km if distancia_km > km_gratis else 0.0
    v_quebra = custo_ingredientes_total * (perc_quebra / 100)
    v_despesas = custo_ingredientes_total * (perc_despesas / 100)
    v_cmv = custo_ingredientes_total + v_quebra + valor_embalagem
    custo_total_prod = v_cmv + v_despesas
    lucro_valor = custo_total_prod * (margem_lucro / 100)
    preco_venda_produto = custo_total_prod + lucro_valor
    t_percentual = (taxa_credito_input / 100) if forma_pagamento == "Crédito" else 0.0
    v_taxa_financeira = (preco_venda_produto + taxa_entrega_base) * t_percentual
    preco_venda_final = preco_venda_produto + taxa_entrega_base + v_taxa_financeira
    cmv_percentual = (v_cmv / preco_venda_produto * 100) if preco_venda_produto > 0 else 0
    cor_cmv = "#4ade80" if cmv_percentual <= 35 else "#facc15" if cmv_percentual <= 45 else "#f87171"

    # --- RESULTADO FINAL (image_63ec02.png) ---
    st.markdown(f"""
    <div class='resultado-box'>
        <p style='margin:0; font-size:14px; opacity: 0.8;'>VALOR SUGERIDO</p>
        <h1 style='color: #60a5fa !important; font-size:48px;'>R$ {preco_venda_final:.2f}</h1>
        <p><b>Lucro Líquido:</b> <span style='color: #4ade80;'>R$ {lucro_valor:.2f}</span></p>
    </div>
    """, unsafe_allow_html=True)

    # --- ABA DE ORÇAMENTO (image_64068d.png / image_64d8c1.png) ---
    st.divider()
    st.header("📋 Orçamento Personalizado")
    
    col_o1, col_o2, col_o3 = st.columns([2, 1, 1])
    with col_o1: nome_c = st.text_input("Nome do Cliente")
    with col_o2: tel_c = st.text_input("Telefone")
    with col_o3: data_o = st.date_input("Data", value=date.today())

    col_i1, col_i2, col_i3, col_i4, col_i5 = st.columns([2.5, 0.8, 1, 1, 1])
    with col_i1:
        ing_opcoes = [""] + df_ing['nome'].tolist()
        item_sel = st.selectbox("Selecione o Ingrediente/Insumo:", options=ing_opcoes, key="orc_sel")
    with col_i2:
        qtd_orc = st.number_input("Qtd", min_value=0.01, value=1.0, key="orc_qtd")
    with col_i3:
        frete_orc = st.number_input("Frete (R$)", min_value=0.0, value=0.0, key="orc_frete")
    with col_i4:
        emb_orc = st.number_input("Emb. (R$)", min_value=0.0, value=0.0, key="orc_emb")
    with col_i5:
        st.write("")
        if st.button("➕ Adicionar", use_container_width=True):
            if item_sel:
                dados_i = df_ing[df_ing['nome'] == item_sel].iloc[0]
                preco_b = float(dados_i['preco'])
                # Preço Unitário no carrinho = (Preço Base * Qtd) + Adicionais
                sub = (preco_b * qtd_orc) + frete_orc + emb_orc
                st.session_state.carrinho.append({
                    "Item": item_sel, "Qtd": qtd_orc, "Preço Unit.": preco_b, "Subtotal": sub
                })
                st.rerun()

    # --- TABELA DE ORÇAMENTO (image_64d8c1.png) ---
    if st.session_state.carrinho:
        df_c = pd.DataFrame(st.session_state.carrinho)
        st.table(df_c.style.format({"Preço Unit.": "R$ {:.2f}", "Subtotal": "R$ {:.2f}"}))
        total_g = df_c["Subtotal"].sum()
        st.markdown(f"## **Total: R$ {total_g:.2f}**")
        
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            if st.button("📲 Gerar Orçamento para WhatsApp", use_container_width=True):
                itens_txt = "".join([f"• {i['Item']} ({i['Qtd']}x): R$ {i['Subtotal']:.2f}\n" for i in st.session_state.carrinho])
                msg = f"*ORÇAMENTO - {data_o.strftime('%d/%m/%Y')}*\n👤 *Cliente:* {nome_c}\n--------------------------\n{itens_txt}--------------------------\n💰 *TOTAL: R$ {total_g:.2f}*"
                st.code(msg, language="text")
        with c_w2:
            if st.button("🗑️ Limpar Pedido", use_container_width=True):
                st.session_state.carrinho = []
                st.rerun()

if __name__ == "__main__":
    main()
