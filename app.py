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

# 2. Estilização CSS para melhor visualização
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

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador & Gerador de Orçamento</h1>", unsafe_allow_html=True)

    # --- SIDEBAR: AJUSTE DE TAXAS ---
    with st.sidebar:
        st.header("⚙️ Ajuste de Taxas")
        taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
        st.divider()
        km_gratis = st.number_input("KM Isentos", value=5)
        valor_por_km = st.number_input("R$ por KM adicional", value=2.0, step=0.1)

    # --- ÁREA DE PRECIFICAÇÃO (MANTIDA DO SEU ORIGINAL) ---
    with st.expander("📝 Precificar Nova Receita"):
        col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
        with col_p1:
            nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod_input")
        with col_p2:
            margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=135)
        with col_p3:
            distancia_km = st.number_input("Distância (km)", min_value=0.0, value=0.0)
        with col_p4:
            forma_pagamento = st.selectbox("Pagamento", ["Crédito", "PIX"])
            
        # Lógica de cálculo simplificada para o exemplo
        custo_base = 0.0 # Aqui entrariam os cálculos de ingredientes que você já possui
        st.info("Utilize esta seção para calcular o custo base antes de gerar o orçamento.")

    # ==========================================
    # --- GERADOR DE ORÇAMENTO (CORRIGIDO) ---
    # ==========================================
    st.divider()
    tab_gerar, tab_salvos = st.tabs(["📋 Gerar Novo Orçamento", "📂 Orçamentos Salvos"])

    with tab_gerar:
        st.subheader("1. Dados do Cliente & Produto")
        c_cli1, c_cli2, c_cli3 = st.columns([2, 1, 1])
        nome_cliente = c_cli1.text_input("Nome do Cliente", placeholder="Ex: João Silva")
        tel_cliente = c_cli2.text_input("Telefone/WhatsApp", placeholder="(00) 00000-0000")
        data_orc_input = c_cli3.date_input("Data", value=date.today())
        
        # O NOME DO PRODUTO É O TÍTULO DO GRUPO
        nome_produto_grupo = st.text_input("📌 Nome do Produto (Título do Grupo)", placeholder="Ex: Bolo de Casamento - 3 Andares")

        st.divider()
        st.subheader("2. Adicionar Itens ao Produto")
        
        co1, co2, co3, co4 = st.columns([2, 1, 1, 1])
        lista_nomes_ing = [""] + df_ing['nome'].tolist() if not df_ing.empty else [""]
        item_planilha_sel = co1.selectbox("Selecionar Ingrediente/Base:", options=lista_nomes_ing)
        
        qtd_orc = co2.number_input("Quantidade", min_value=1, value=1)
        taxa_f_orc = co3.number_input("Frete do Item (R$)", min_value=0.0, value=0.0)
        taxa_e_orc = co4.number_input("Embalagem (R$)", min_value=0.0, value=0.0)

        if st.button("➕ Adicionar Item"):
            if item_planilha_sel != "" and nome_produto_grupo != "":
                # CORREÇÃO INDEX OUT OF BOUNDS: Busca segura do preço
                filtro_preco = df_ing[df_ing['nome'] == item_planilha_sel]
                if not filtro_preco.empty:
                    preco_unit = float(filtro_preco['preco'].iloc[0])
                    subtotal = (preco_unit * qtd_orc) + taxa_f_orc + taxa_e_orc
                    
                    # CORREÇÃO KEYERROR: Salvando a chave 'Item' corretamente
                    st.session_state.carrinho_orc.append({
                        "Item": item_planilha_sel,
                        "Qtd": qtd_orc,
                        "Frete": taxa_f_orc,
                        "Emb": taxa_e_orc,
                        "Total": subtotal
                    })
                    st.rerun()
                else:
                    st.error("Item não encontrado na planilha de ingredientes.")
            else:
                st.warning("Preencha o Nome do Produto e selecione um Item.")

        # EXIBIÇÃO DOS ITENS ADICIONADOS
        if st.session_state.carrinho_orc:
            st.markdown(f"### 📦 {nome_produto_grupo}")
            st.write(f"**Cliente:** {nome_cliente} | **Tel:** {tel_cliente} | **Data:** {data_orc_input.strftime('%d/%m/%Y')}")
            
            for idx, it in enumerate(st.session_state.carrinho_orc):
                cols = st.columns([3, 1, 1, 1, 1, 0.5])
                # CORREÇÃO KEYERROR: Acesso seguro à chave
                nome_item = it.get('Item', 'Desconhecido')
                cols[0].write(f"🔹 {nome_item}")
                cols[1].write(f"x{it['Qtd']}")
                cols[2].write(f"F: R${it['Frete']:.2f}")
                cols[3].write(f"E: R${it['Emb']:.2f}")
                cols[4].write(f"**R$ {it['Total']:.2f}**")
                
                # Botão de deletar item específico
                if cols[5].button("❌", key=f"del_{idx}"):
                    st.session_state.carrinho_orc.pop(idx)
                    st.rerun()
            
            total_geral = sum(x['Total'] for x in st.session_state.carrinho_orc)
            st.markdown(f"## **Total do Orçamento: R$ {total_geral:.2f}**")

            # BOTÕES DE AÇÃO
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("📱 Gerar WhatsApp", use_container_width=True):
                    msg = f"*ORÇAMENTO: {nome_produto_grupo}*\n"
                    msg += f"Data: {data_orc_input.strftime('%d/%m/%Y')}\n"
                    msg += f"Cliente: {nome_cliente}\n"
                    msg += "-"*20 + "\n"
                    for i in st.session_state.carrinho_orc:
                        msg += f"• {i['Item']} (x{i['Qtd']}): R$ {i['Total']:.2f}\n"
                    msg += "-"*20 + "\n"
                    msg += f"*TOTAL: R$ {total_geral:.2f}*"
                    st.code(msg, language="text")
            
            with b2:
                if st.button("💾 Salvar Orçamento", use_container_width=True):
                    df_save = pd.DataFrame([{
                        "Data": data_orc_input.strftime('%d/%m/%Y'),
                        "Cliente": nome_cliente,
                        "Produto": nome_produto_grupo,
                        "Total": f"R$ {total_geral:.2f}"
                    }])
                    hist = carregar_orcamentos_salvos()
                    novo_hist = pd.concat([hist, df_save], ignore_index=True)
                    conn.update(worksheet="Orcamentos_Salvos", data=novo_hist)
                    st.success("Orçamento salvo na aba de históricos!")

            with b3:
                if st.button("🗑️ Limpar Tudo", use_container_width=True):
                    st.session_state.carrinho_orc = []
                    st.rerun()

    with tab_salvos:
        df_historico = carregar_orcamentos_salvos()
        if not df_historico.empty:
            st.dataframe(df_historico, use_container_width=True)
        else:
            st.info("Nenhum orçamento salvo encontrado.")

if __name__ == "__main__":
    main()
