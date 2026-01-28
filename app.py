import streamlit as st
import pandas as pd
import os
import urllib.parse

# 1. Configuração da Página
st.set_page_config(page_title="Precificador", page_icon="📊", layout="wide")

# 2. Estilização CSS
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .titulo-planilha { color: #1e3a8a; font-weight: bold; border-bottom: 2px solid #1e3a8a; margin-bottom: 20px; text-align: center; }
    .resultado-box { 
        background-color: #262730; padding: 25px; border-radius: 15px; border-left: 10px solid #1e3a8a; 
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

# --- SIDEBAR: TAXAS ---
with st.sidebar:
    st.header("⚙️ Ajuste de Taxas")
    taxa_debito_input = st.number_input("Taxa Débito (%)", value=1.99, step=0.01)
    taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
    st.divider()
    km_gratis = st.number_input("KM Isentos", value=5)
    valor_por_km = st.number_input("R$ por KM adicional", value=2.0, step=0.5)

def main():
    df_ing = carregar_ingredientes()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador & Orçamento Profissional</h1>", unsafe_allow_html=True)
    
    # --- INPUTS DE CABEÇALHO ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1: nome_prod = st.text_input("Nome do Produto:", key="n_prod", placeholder="Ex: Brownie Recheado")
    with col_p2: margem = st.number_input("Margem (%)", min_value=0, value=150)
    with col_p3: dist = st.number_input("Distância (km)", min_value=0.0, value=None, placeholder="0.0")
    with col_p4: pgto = st.selectbox("Pagamento", ["PIX", "Débito", "Crédito"])

    st.divider()
    col_esq, col_dir = st.columns([2, 1])
    
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens = st.number_input("Itens na receita:", min_value=1, value=1)
        custo_ing = 0.0
        for i in range(int(n_itens)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1: item = st.selectbox(f"Item {i+1}", df_ing['nome'].tolist(), key=f"p_n_{i}")
            with c2: qtd = st.number_input(f"Qtd", min_value=0.0, value=None, key=f"p_q_{i}", placeholder="0.0")
            with c3: unid = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"p_u_{i}")
            
            # Cálculo de Custo Corrigido
            dados = df_ing[df_ing['nome'] == item].iloc[0]
            val_q = qtd if qtd is not None else 0.0
            base_u = str(dados['unidade']).lower().strip()
            
            fator = 1.0
            if unid == "g" and base_u == "kg": fator = 0.001
            elif unid == "kg" and base_u == "g": fator = 1000.0
            elif unid == "ml" and base_u == "l": fator = 0.001
            elif unid == "l" and base_u == "ml": fator = 1000.0
            
            custo_parcial = (val_q * fator) * float(dados['preco'])
            custo_ing += custo_parcial
            with c4: st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    with col_dir:
        st.subheader("⚙️ Adicionais")
        p_quebra = st.slider("Quebra (%)", 0, 15, 5)
        p_fixo = st.slider("Despesas Fixas (%)", 0, 100, 30)
        v_emb = st.number_input("Embalagem (R$)", min_value=0.0, value=None, placeholder="0.0")

    # --- CÁLCULOS ---
    v_dist = dist if dist is not None else 0.0
    v_e = v_emb if v_emb is not None else 0.0
    taxa_e = (v_dist - km_gratis) * valor_por_km if v_dist > km_gratis else 0.0
    
    v_q = custo_ing * (p_quebra / 100)
    v_f = custo_ing * (p_fixo / 100)
    cmv_v = custo_ing + v_q + v_e
    
    preco_p = (cmv_v + v_f) * (1 + margem/100)
    
    t_f = (taxa_credito_input/100 if pgto == "Crédito" else taxa_debito_input/100 if pgto == "Débito" else 0.0)
    v_taxa_f = (preco_p + taxa_e) * t_f
    preco_final = preco_p + taxa_e + v_taxa_f
    
    cmv_p = (cmv_v / preco_p * 100) if preco_p > 0 else 0.0

    # --- EXIBIÇÃO ---
    st.divider()
    r1, r2 = st.columns([1.5, 1])
    with r1:
        st.markdown("### Detalhamento Financeiro")
        df_res = pd.DataFrame({
            "Item": ["Custo Ingredientes", "Quebra/Desperdício", "Despesas Gerais", "Embalagem", "Custo Produção", "Lucro Bruto", f"Entrega ({v_dist}km)", f"Taxa {pgto}", "TOTAL"],
            "Valor": [f"R$ {custo_ing:.2f}", f"R$ {v_q:.2f}", f"R$ {v_f:.2f}", f"R$ {v_e:.2f}", f"R$ {cmv_v + v_f:.2f}", f"R$ {preco_p - (cmv_v + v_f):.2f}", f"R$ {taxa_e:.2f}", f"R$ {v_taxa_f:.2f}", f"R$ {preco_final:.2f}"]
        })
        st.table(df_res)

    with r2:
        cor = "#4ade80" if cmv_p <= 35 else "#facc15" if cmv_p <= 45 else "#f87171"
        st.markdown(f"""
            <div class='resultado-box'>
                <p style='margin:0; font-size:14px; opacity: 0.8;'>{nome_prod.upper() if nome_prod else 'ORÇAMENTO'}</p>
                <h2 style='margin:0;'>TOTAL A COBRAR</h2>
                <h1 style='color: #60a5fa !important; font-size:48px;'>R$ {preco_final:.2f}</h1>
                <hr style='border-color: #4b5563;'>
                <p style='font-size: 22px;'>CMV: <span style='color:{cor}; font-weight: bold;'>{cmv_p:.1f}%</span></p>
                <p><b>Lucro Líquido:</b> <span style='color: #4ade80;'>R$ {preco_p - (cmv_v + v_f):.2f}</span></p>
            </div>
        """, unsafe_allow_html=True)
        
        # --- BOTÃO DE ORÇAMENTO WHATSAPP ---
        st.write("")
        nome_display = nome_prod if nome_prod else "[Nome do Produto]"
        texto_whats = (
            f"Olá! Segue o orçamento para *{nome_display}*:\n\n"
            f"Valor unitário: R$ {preco_p:.2f}\n"
            f"Entrega ({v_dist} km): R$ {taxa_e:.2f}\n"
            f"*Total: R$ {preco_final:.2f}* (Pagamento via {pgto})\n\n"
            f"Aguardamos seu pedido!"
        )
        
        link_whats = f"https://wa.me/?text={urllib.parse.quote(texto_whats)}"
        st.markdown(f"""
            <a href="{link_whats}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 16px; cursor: pointer;">
                    📲 Gerar Pedido para WhatsApp
                </div>
            </a>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
