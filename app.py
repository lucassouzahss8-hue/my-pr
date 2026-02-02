import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página
st.set_page_config(
    page_title="Precificador", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Estilização CSS
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
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO BANCO DE DADOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- INICIALIZAÇÃO DO ESTADO ---
if "n_itens" not in st.session_state:
    st.session_state.n_itens = 1
if "nome_prod" not in st.session_state:
    st.session_state.nome_prod = ""

# --- FUNÇÕES DE DADOS ---
def carregar_ingredientes():
    try:
        df = conn.read(worksheet="Ingredientes", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['nome', 'unidade', 'preco'])
        df.columns = [str(c).strip().lower() for c in df.columns]
        if 'preco' in df.columns:
            df['preco'] = pd.to_numeric(df['preco'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar aba 'Ingredientes': {e}")
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

    # --- SIDEBAR: TAXAS (DÉBITO REMOVIDO) ---
    with st.sidebar:
        st.header("⚙️ Ajuste de Taxas")
        taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
        km_gratis = st.number_input("KM Isentos", value=5)
        valor_km = st.number_input("R$ por KM adicional", value=2.0, step=0.1)

    # --- GERENCIAR RECEITAS ---
    with st.expander("📂 Abrir ou Deletar Receitas Salvas"):
        receitas_nomes = df_rec['nome_receita'].unique().tolist() if not df_rec.empty else []
        col_rec1, col_rec2 = st.columns([3, 1])
        with col_rec1:
            selecionada = st.selectbox("Selecione uma receita:", [""] + receitas_nomes)
        with col_rec2:
            st.write("")
            if st.button("🔄 Carregar", use_container_width=True) and selecionada != "":
                dados = df_rec[df_rec['nome_receita'] == selecionada]
                st.session_state.nome_prod = selecionada
                st.session_state.n_itens = len(dados)
                for idx, row in enumerate(dados.itertuples()):
                    st.session_state[f"nome_{idx}"] = row.ingrediente
                    st.session_state[f"qtd_{idx}"] = float(row.qtd)
                    st.session_state[f"u_{idx}"] = row.unid
                st.rerun()

    # --- CONFIGURAÇÕES DO PRODUTO ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1:
        nome_final = st.text_input("Nome do Produto:", key="nome_prod")
    with col_p2:
        margem = st.number_input("Lucro (%)", min_value=0, value=150)
    with col_p3:
        distancia = st.number_input("Distância (km)", min_value=0.0, value=0.0, step=0.1)
    with col_p4:
        # Crédito como primeira opção para cálculo automático inicial
        pagamento = st.selectbox("Pagamento", ["Crédito", "PIX"])

    if df_ing.empty:
        st.warning("⚠️ Adicione ingredientes na aba 'Ingredientes' da sua planilha.")
        return

    # --- ÁREA DE CÁLCULO ---
    st.divider()
    col_esq, col_dir = st.columns([2, 1])
    
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens = st.number_input("Qtd de Itens:", min_value=1, key="n_itens")
        custo_total_ing = 0.0
        lista_save = []

        for i in range(int(n_itens)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                lista_nomes = df_ing['nome'].tolist()
                idx_default = 0
                if f"nome_{i}" in st.session_state and st.session_state[f"nome_{i}"] in lista_nomes:
                    idx_default = lista_nomes.index(st.session_state[f"nome_{i}"])
                item_escolhido = st.selectbox(f"Item {i+1}", options=lista_nomes, key=f"nome_{i}", index=idx_default)
            
            dados_item = df_ing[df_ing['nome'] == item_escolhido].iloc[0]
            with c2:
                qtd = st.number_input(f"Qtd", key=f"qtd_{i}", step=0.01, value=st.session_state.get(f"qtd_{i}", 0.0))
            with c3:
                unid = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")

            fator = 1.0
            u_base = str(dados_item['unidade']).lower().strip()
            if unid == "g" and u_base == "kg": fator = 1/1000
            elif unid == "kg" and u_base == "g": fator = 1000
            elif unid == "ml" and u_base == "l": fator = 1/1000
            
            custo_item = (qtd * fator) * float(dados_item['preco'])
            custo_total_ing += custo_item
            lista_save.append({"nome_receita": nome_final, "ingrediente": item_escolhido, "qtd": qtd, "unid": unid})
            
            with c4:
                st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_item:.2f}</p>", unsafe_allow_html=True)

    # --- RESULTADOS ---
    with col_dir:
        st.subheader("📊 Resumo")
        v_emb = st.number_input("Embalagem (R$)", value=0.0, step=0.1)
        v_quebra = custo_total_ing * 0.05
        custo_producao = custo_total_ing + v_quebra + v_emb
        lucro_valor = custo_producao * (margem / 100)
        
        v_entrega = (distancia - km_gratis) * valor_km if distancia > km_gratis else 0.0
        
        # Lógica de Taxa (Apenas Crédito ou Zero para PIX)
        taxa_perc = taxa_credito_input if pagamento == "Crédito" else 0.0
        
        total_sem_taxa = custo_producao + lucro_valor + v_entrega
        v_financeiro = total_sem_taxa * (taxa_perc / 100)
        total_final = total_sem_taxa + v_financeiro

        st.markdown(f"""
        <div class='resultado-box'>
            <h2 style='color:white; margin-bottom:0;'>Total a Cobrar</h2>
            <h1 style='color:#60a5fa; font-size:45px; margin-top:0;'>R$ {total_final:.2f}</h1>
            <hr style='opacity:0.3'>
            <p style='margin:0;'><b>Custo Prod:</b> R$ {custo_producao:.2f}</p>
            <p style='margin:0;'><b>Taxa {pagamento}:</b> R$ {v_financeiro:.2f}</p>
            <p style='margin:0;'><b>Entrega:</b> R$ {v_entrega:.2f}</p>
            <p style='font-size:18px; margin-top:10px;'><b>Lucro Líquido: <span style='color:#4ade80;'>R$ {lucro_valor:.2f}</span></b></p>
        </div>
        """, unsafe_allow_html=True)

        st.write("")
        if st.button("💾 Salvar Receita", use_container_width=True):
            if nome_final:
                df_nova = pd.DataFrame(lista_save)
                df_final = pd.concat([df_rec[df_rec['nome_receita'] != nome_final], df_nova], ignore_index=True)
                conn.update(worksheet="Receitas", data=df_final)
                st.success(f"Receita '{nome_final}' salva!")
                st.rerun()
            else:
                st.warning("Dê um nome ao produto primeiro.")

if __name__ == "__main__":
    main()
