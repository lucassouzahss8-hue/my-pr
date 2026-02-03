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
if "preco_calculado" not in st.session_state:
    st.session_state.preco_calculado = 0.0

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
        if df is None or df.empty or 'nome_receita' not in df.columns:
            return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])
        return df
    except Exception:
        return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas_nuvem()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador</h1>", unsafe_allow_html=True)

    # --- ABA DE SELEÇÃO DE RECEITA ORIGINAL ---
    with st.expander("📂 Abrir ou Deletar Receitas Salvas"):
        receitas_nomes = df_rec['nome_receita'].unique().tolist() if not df_rec.empty else []
        col_rec1, col_rec2 = st.columns([3, 1])
        with col_rec1:
            receita_selecionada = st.selectbox("Selecione uma receita:", [""] + receitas_nomes)
        with col_rec2:
            st.write("") 
            if st.button("🔄 Carregar", use_container_width=True) and receita_selecionada != "":
                dados_rec = df_rec[df_rec['nome_receita'] == receita_selecionada]
                st.session_state.nome_prod = receita_selecionada
                st.session_state.n_itens = len(dados_rec)
                for idx, row in enumerate(dados_rec.itertuples()):
                    st.session_state[f"nome_{idx}"] = row.ingrediente
                    st.session_state[f"qtd_{idx}"] = float(row.qtd)
                    st.session_state[f"u_{idx}"] = row.unid
                st.rerun()

    # --- CONFIGURAÇÕES DO PRODUTO (VALORES PADRÃO 135%, 2%, 30%) ---
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

    # --- ÁREA DOS INGREDIENTES E ADICIONAIS ---
    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens_input = st.number_input("Número de itens:", min_value=1, key="n_itens")
        custo_ingredientes_total = 0.0
        for i in range(int(n_itens_input)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                lista_nomes = df_ing['nome'].tolist()
                idx_def = lista_nomes.index(st.session_state[f"nome_{i}"]) if f"nome_{i}" in st.session_state and st.session_state[f"nome_{i}"] in lista_nomes else 0
                escolha = st.selectbox(f"Item {i+1}", options=lista_nomes, key=f"nome_{i}", index=idx_def)
            dados_item = df_ing[df_ing['nome'] == escolha].iloc[0]
            with c2:
                qtd_usada = st.number_input(f"Qtd", key=f"qtd_{i}", step=0.01, value=st.session_state.get(f"qtd_{i}", 0.0))
            with c3:
                unid_uso = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")
            
            fator = 1.0
            u_base = str(dados_item['unidade']).lower().strip()
            if unid_uso == "g" and u_base == "kg": fator = 1/1000
            elif unid_uso == "ml" and u_base == "l": fator = 1/1000
            
            custo_parcial = (qtd_usada * fator) * float(dados_item['preco'])
            custo_ingredientes_total += custo_parcial
            with c4:
                st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra (%)", 0, 15, 2)
        perc_despesas = st.slider("Despesas Gerais (%)", 0, 100, 30)
        valor_embalagem = st.number_input("Embalagem (R$)", min_value=0.0, value=0.0)

    # --- CÁLCULOS TÉCNICOS ---
    v_quebra = custo_ingredientes_total * (perc_quebra / 100)
    v_despesas = custo_ingredientes_total * (perc_despesas / 100)
    custo_total_prod = custo_ingredientes_total + v_quebra + v_despesas + valor_embalagem
    lucro_valor = custo_total_prod * (margem_lucro / 100)
    preco_venda_final = custo_total_prod + lucro_valor
    
    # Atualiza o estado global para o Orçamento usar
    st.session_state.preco_calculado = preco_venda_final

    # --- TABELA DE DETALHAMENTO ORIGINAL ---
    st.divider()
    res1, res2 = st.columns([1.5, 1])
    with res1:
        st.markdown(f"### Detalhamento: {nome_produto_final}")
        df_resumo = pd.DataFrame({
            "Item": ["Ingredientes", "Quebra (2%)", "Despesas (30%)", "Lucro (135%)", "TOTAL FINAL"],
            "Valor": [f"R$ {custo_ingredientes_total:.2f}", f"R$ {v_quebra:.2f}", f"R$ {v_despesas:.2f}", f"R$ {lucro_valor:.2f}", f"R$ {preco_venda_final:.2f}"]
        })
        st.table(df_resumo)

    with res2:
        st.markdown(f"""
        <div class='resultado-box'>
            <p style='margin:0; font-size:14px; opacity: 0.8;'>VALOR DA RECEITA</p>
            <h1 style='color: #60a5fa !important; font-size:48px;'>R$ {preco_venda_final:.2f}</h1>
        </div>
        """, unsafe_allow_html=True)

    # --- ABA ORÇAMENTO (PUXANDO VALORES SALVOS) ---
    st.divider()
    st.markdown("## 📝 Aba de Orçamento")
    
    with st.container():
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            nome_cli = st.text_input("Nome do Cliente")
        with col_c2:
            tel_cli = st.text_input("Telefone")
        with col_c3:
            dt_orc = st.date_input("Data", value=date.today())

        col_v1, col_v2, col_v3 = st.columns([2, 1, 1])
        with col_v1:
            # O nome do produto já vem da receita selecionada
            st.markdown(f"**Produto:** {nome_produto_final}")
        with col_v2:
            # O valor unitário é travado no valor da receita selecionada
            st.markdown(f"**Valor Unitário:** R$ {st.session_state.preco_calculado:.2f}")
        with col_v3:
            qtd_final = st.number_input("Quantidade", min_value=1, value=1)

        # CAMPO DE TAXA DE ENTREGA PEDIDO
        taxa_entrega = st.number_input("Taxa de Entrega (R$)", min_value=0.0, value=0.0)
        
        total_orcamento = (st.session_state.preco_calculado * qtd_final) + taxa_entrega
        st.markdown(f"### Total: R$ {total_orcamento:.2f}")

        if st.button("Gerar orçamento para whatsapp"):
            texto_zap = f"""
📋 *ORÇAMENTO*
📅 Data: {dt_orc.strftime('%d/%m/%Y')}
👤 Cliente: {nome_cli}
📞 Tel: {tel_cli}
--------------------------
🍰 Produto: {nome_produto_final}
🔢 Quantidade: {qtd_final}
💰 Valor Unit.: R$ {st.session_state.preco_calculado:.2f}
🚚 Taxa de Entrega: R$ {taxa_entrega:.2f}
--------------------------
✅ *TOTAL: R$ {total_orcamento:.2f}*
"""
            st.code(texto_zap, language="text")
            st.success("Copiado com sucesso!")

if __name__ == "__main__":
    main()
