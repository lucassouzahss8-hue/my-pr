import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date

# 1. Configuração da Página
st.set_page_config(
    page_title="Precificador Profissional", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Estilização CSS (Sua base visual original)
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
if "carrinho_orc" not in st.session_state:
    st.session_state.carrinho_orc = []

# --- FUNÇÕES DE CARREGAMENTO (Sua base estável) ---
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

def carregar_orcamentos_salvos():
    try:
        df = conn.read(worksheet="Orcamentos_Salvos", ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas_nuvem()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador e Orçamentos</h1>", unsafe_allow_html=True)

    # --- SIDEBAR: AJUSTE DE TAXAS ---
    with st.sidebar:
        st.header("⚙️ Configurações de Taxas")
        taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
        st.divider()
        km_gratis = st.number_input("KM Isentos", value=5)
        valor_por_km = st.number_input("R$ por KM adicional", value=2.0, step=0.1)

    # --- ÁREA DE PRECIFICAÇÃO DE PRODUTO (Base Original) ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1:
        nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod")
    with col_p2:
        margem_lucro_input = st.number_input("Margem de Lucro (%)", min_value=0, value=135)
    with col_p3:
        distancia_km_input = st.number_input("Distância (km)", min_value=0.0, value=0.0, step=0.1)
    with col_p4:
        forma_pagamento_input = st.selectbox("Pagamento", ["Crédito", "PIX"])
        
    st.divider()

    # (A lógica de ingredientes e cálculos do precificador permanece a mesma da sua base...)
    # ... [Omitido para brevidade, mas mantido no seu código real] ...

    # --- GERADOR DE ORÇAMENTOS (ATUALIZADO CONFORME SOLICITADO) ---
    st.markdown("<h2 class='titulo-planilha'>📋 Gerador de Orçamentos Detalhado</h2>", unsafe_allow_html=True)
    tab_gerar, tab_salvos = st.tabs(["🆕 Criar Orçamento", "📂 Histórico"])

    with tab_gerar:
        c_cli1, c_cli2, c_cli3 = st.columns([2, 1, 1])
        nome_cliente = c_cli1.text_input("Nome do Cliente", placeholder="Ex: Maria Silva")
        tel_cliente = c_cli2.text_input("Telefone", placeholder="(00) 00000-0000")
        data_orc_input = c_cli3.date_input("Data do Orçamento", value=date.today())
        
        nome_pedido_grupo = st.text_input("📌 Nome do Pedido", placeholder="Ex: Kit Trufas Aniversário")

        st.divider()
        # Seleção de itens baseada na sua planilha de ingredientes
        co1, co2, co3, co4 = st.columns([3, 1, 1, 1])
        item_sel = co1.selectbox("Selecione o Item da Planilha:", options=[""] + df_ing['nome'].tolist(), key="sel_item_orc")
        qtd_orc = co2.number_input("Qtd", min_value=1, value=1, key="qtd_item_orc")
        f_orc = co3.number_input("Frete/Item (R$)", min_value=0.0, value=0.0)
        e_orc = co4.number_input("Emb./Item (R$)", min_value=0.0, value=0.0)

        if st.button("➕ Adicionar ao Pedido"):
            if item_sel != "" and nome_pedido_grupo != "":
                filtro = df_ing[df_ing['nome'] == item_sel]
                if not filtro.empty:
                    # Custo real direto da sua base
                    p_base_puro = float(filtro['preco'].iloc[0])
                    
                    st.session_state.carrinho_orc.append({
                        "Item": item_sel, 
                        "Qtd": qtd_orc, 
                        "Custo_Puro": p_base_puro,
                        "Frete": f_orc,
                        "Emb": e_orc
                    })
                    st.rerun()

        if st.session_state.carrinho_orc:
            st.markdown(f"### 📦 Resumo: {nome_pedido_grupo}")
            total_custos_sem_nada = 0.0
            total_venda_acumulado = 0.0

            # Cabeçalho da Tabela
            h1, h2, h3, h4, h5, h6 = st.columns([3, 1, 1.5, 1.5, 2, 0.5])
            h1.write("**Item**")
            h2.write("**Qtd**")
            h3.write("**Custo Unit. (Puro)**")
            h4.write("**Venda Unit. (+ Lucro)**")
            h5.write("**Subtotal Venda**")

            for idx, it in enumerate(st.session_state.carrinho_orc):
                cols = st.columns([3, 1, 1.5, 1.5, 2, 0.5])
                q = it['Qtd']
                c_puro = it['Custo_Puro']
                
                # Venda unitária: (Custo + Adicionais) * Margem definida na tela
                venda_unitario = (c_puro + it['Frete'] + it['Emb']) * (1 + (margem_lucro_input / 100))
                subtotal_venda = venda_unitario * q
                
                total_custos_sem_nada += (c_puro * q)
                total_venda_acumulado += subtotal_venda
                
                cols[0].write(f"🔹 {it['Item']}")
                cols[1].write(f"x{q}")
                cols[2].write(f"R$ {c_puro:.2f}") # VALOR UNITÁRIO SEM NADA
                cols[3].write(f"R$ {venda_unitario:.2f}") # VALOR COM LUCRO
                cols[4].write(f"**R$ {subtotal_venda:.2f}**")
                
                if cols[5].button("❌", key=f"del_orc_{idx}"):
                    st.session_state.carrinho_orc.pop(idx)
                    st.rerun()
            
            st.divider()
            
            # --- TOTAIS FINAIS ---
            # Frete por distância da sua base original
            v_entrega_final = (distancia_km_input - km_gratis) * valor_por_km if distancia_km_input > km_gratis else 0.0
            
            # Taxa de cartão
            valor_base_taxas = total_venda_acumulado + v_entrega_final
            v_taxa_cartao = valor_base_taxas * (taxa_credito_input / 100) if forma_pagamento_input == "Crédito" else 0.0
            
            total_geral_orc = valor_base_taxas + v_taxa_cartao

            col_fin1, col_fin2 = st.columns([1.5, 1])
            with col_fin1:
                st.markdown("#### 🛠️ Resumo de Custos")
                st.write(f"Valor Unitário total (Sem acréscimos): **R$ {total_custos_sem_nada:.2f}**")
                st.write(f"Soma com Lucro ({margem_lucro_input}%): R$ {total_venda_acumulado:.2f}")
                st.write(f"Entrega: R$ {v_entrega_final:.2f}")
            
            with col_fin2:
                st.markdown("#### 💳 Total com Taxas")
                if forma_pagamento_input == "Crédito":
                    st.write(f"Taxa Cartão ({taxa_credito_input}%): R$ {v_taxa_cartao:.2f}")
                st.markdown(f"<h2 style='color: #4ade80;'>Total Final: R$ {total_geral_orc:.2f}</h2>", unsafe_allow_html=True)

    # (Histórico e botões de salvar permanecem os mesmos da base...)

if __name__ == "__main__":
    main()
