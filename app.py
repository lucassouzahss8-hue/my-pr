import streamlit as st
import pandas as pd
import os

# 1. Configuração da Página
st.set_page_config(page_title="Precificador", page_icon="📊", layout="wide")

# 2. Estilização CSS
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .titulo-planilha { color: #1e3a8a; font-weight: bold; border-bottom: 2px solid #1e3a8a; margin-bottom: 20px; text-align: center; }
    .resultado-box { 
        background-color: #262730; 
        padding: 25px; border-radius: 15px; border-left: 10px solid #1e3a8a; 
        box-shadow: 2px 2px 15px rgba(0,0,0,0.3); color: white; 
    }
    .resultado-box h1, .resultado-box h2, .resultado-box p, .resultado-box b { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def carregar_ingredientes():
    try:
        df = pd.read_csv("ingredientes.csv")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except: return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

# --- SIDEBAR: PAINEL DE TAXAS ---
with st.sidebar:
    st.header("⚙️ Ajuste de Taxas")
    st.subheader("Maquininha")
    taxa_debito_input = st.number_input("Taxa Débito (%)", value=1.99, step=0.01)
    taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
    
    st.subheader("Entrega")
    km_gratis = st.number_input("KM Isentos", value=5)
    valor_por_km = st.number_input("Valor por KM adicional", value=2.0, step=0.5)
    
    st.info("Estas taxas serão aplicadas nos cálculos ao lado.")

# --- APP ---
def main():
    df_ing = carregar_ingredientes()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador Profissional</h1>", unsafe_allow_html=True)

    # --- INPUTS PRINCIPAIS ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1:
        nome_produto_final = st.text_input("Nome do Produto:", key="nome_prod", placeholder="Ex: Brownie Recheado")
    with col_p2:
        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=150)
    with col_p3:
        distancia_km = st.number_input("Distância (km)", min_value=0.0, value=None, placeholder="Ex: 6.0")
    with col_p4:
        forma_pagamento = st.selectbox("Pagamento", ["PIX", "Débito", "Crédito"])

    st.divider()

    # --- MONTAGEM DA RECEITA ---
    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens = st.number_input("Itens na receita:", min_value=1, value=1)
        custo_ingredientes_total = 0.0
        for i in range(int(n_itens)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                escolha = st.selectbox(f"Item {i+1}", options=df_ing['nome'].tolist(), key=f"n_{i}")
            with c2:
                qtd = st.number_input(f"Qtd", min_value=0.0, key=f"q_{i}", value=None, placeholder="0.0")
            with c3:
                unid = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")
            
            dados = df_ing[df_ing['nome'] == escolha].iloc[0]
            base_p = float(dados['preco'])
            base_u = str(dados['unidade']).lower().strip()
            
            val_q = qtd if qtd is not None else 0.0
            fator = 1.0
            if unid == "g" and base_u == "kg": fator = 1/1000
            elif unid == "kg" and base_u == "g": fator = 1000
            elif unid == "ml" and base_u == "l": fator = 1/1000
            elif unid == "l" and base_u == "ml": fator = 1000
            
            custo_item = (val_q * fator) * base_p
            custo_ingredientes_total += custo_item
            with c4: st.markdown(f"<p style='padding-top:35px;'>R$ {custo_item:.2f}</p>", unsafe_allow_html=True)

    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra (%)", 0, 15, 5)
        perc_despesas = st.slider("Fixo/Geral (%)", 0, 100, 30)
        v_embalagem = st.number_input("Embalagem (R$)", min_value=0.0, value=None, placeholder="0.0")

    # --- CÁLCULOS UTILIZANDO AS TAXAS DA SIDEBAR ---
    val_dist = distancia_km if distancia_km is not None else 0.0
    val_emb = v_embalagem if v_embalagem is not None else 0.0
    
    # Cálculo Entrega usando valores da sidebar
    taxa_entrega = (val_dist - km_gratis) * valor_por_km if val_dist > km_gratis else 0.0
    
    v_quebra = custo_ingredientes_total * (perc_quebra / 100)
    v_despesas = custo_ingredientes_total * (perc_despesas / 100)
    
    cmv_valor = custo_ingredientes_total + v_quebra + val_emb
    custo_total_prod = cmv_valor + v_despesas
    lucro_valor = custo_total_prod * (margem_lucro / 100)
    preco_produto = custo_total_prod + lucro_valor
    
    # Cálculo Taxa Financeira usando valores da sidebar
    if forma_pagamento == "Débito":
        t_fin = taxa_debito_input / 100
    elif forma_pagamento == "Crédito":
        t_fin = taxa_credito_input / 100
    else:
        t_fin = 0.0
        
    v_taxa_fin = (preco_produto + taxa_entrega) * t_fin
    preco_final = preco_produto + taxa_entrega + v_taxa_fin
    
    cmv_percentual = (cmv_valor / preco_produto) * 100 if preco_produto > 0 else 0

    # --- EXIBIÇÃO ---
    st.divider()
    res1, res2 = st.columns([1.5, 1])
    with res1:
        st.markdown("### Detalhamento Financeiro")
        df_res = pd.DataFrame({
            "Item": ["CMV (Custos Diretos)", "Custos Fixos", "Lucro Bruto", "Entrega", f"Taxa {forma_pagamento}", "TOTAL"],
            "Valor": [f"R$ {cmv_valor:.2f}", f"R$ {v_despesas:.2f}", f"R$ {lucro_valor:.2f}", f"R$ {taxa_entrega:.2f}", f"R$ {v_taxa_fin:.2f}", f"R$ {preco_final:.2f}"]
        })
        st.table(df_res)

    with res2:
        cor_cmv = "#4ade80" if cmv_percentual <= 35 else "#facc15" if cmv_percentual <= 45 else "#f87171"
        st.markdown(f"""
        <div class='resultado-box'>
            <h2 style='margin:0;'>TOTAL A COBRAR</h2>
            <h1 style='color: #60a5fa !important; font-size:48px;'>R$ {preco_final:.2f}</h1>
            <hr>
            <p><b>CMV:</b> <span style='color:{cor_cmv};'>{cmv_percentual:.1f}%</span></p>
            <p><b>Lucro Líquido:</b> <span style='color: #4ade80;'>R$ {lucro_valor:.2f}</span></p>
            <p><small>*Taxas aplicadas via painel lateral.</small></p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
