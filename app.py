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

def carregar_receitas():
    try:
        df = conn.read(worksheet="Receitas", ttl=0)
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas()
    
    st.markdown("<h1 class='titulo-planilha'>📊 Precificador</h1>", unsafe_allow_html=True)

    # --- SIDEBAR ORIGINAL ---
    with st.sidebar:
        st.header("⚙️ Ajuste de Taxas")
        taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99)
        km_gratis = st.number_input("KM Isentos", value=5)
        valor_por_km = st.number_input("R$ por KM adicional", value=2.0)

    # --- GERENCIAR RECEITAS (EXPANDER ORIGINAL) ---
    with st.expander("📂 Abrir ou Deletar Receitas Salvas"):
        receitas_nomes = sorted(df_rec['nome_receita'].unique().tolist()) if not df_rec.empty else []
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

    # --- CONFIGURAÇÕES DO PRODUTO ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1:
        nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod")
    with col_p2:
        margem_lucro = st.number_input("Margem de Lucro (%)", value=135)
    with col_p3:
        distancia_km = st.number_input("Distância (km)", value=0.0)
    with col_p4:
        forma_pagamento = st.selectbox("Pagamento", ["Crédito", "PIX"])
        
    st.divider()

    # --- ÁREA DOS INGREDIENTES ---
    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens_input = st.number_input("Número de itens:", min_value=1, key="n_itens_val", value=st.session_state.n_itens)
        custo_ingredientes_total = 0.0
        lista_para_salvar = []
        
        for i in range(int(n_itens_input)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                lista_nomes = [""] + df_ing['nome'].tolist()
                escolha = st.selectbox(f"Item {i+1}", options=lista_nomes, key=f"nome_{i}")
            
            if escolha:
                dados_item = df_ing[df_ing['nome'] == escolha].iloc[0]
                with c2:
                    qtd_usada = st.number_input(f"Qtd", key=f"qtd_{i}", step=0.01, value=st.session_state.get(f"qtd_{i}", 0.0))
                with c3:
                    unid_uso = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")
                
                fator = 1.0
                u_base = str(dados_item['unidade']).lower().strip()
                if unid_uso == "g" and u_base == "kg": fator = 1/1000
                elif unid_uso == "ml" and u_base == "l": fator = 1/1000
                
                custo_parcial = (float(qtd_usada) * fator) * float(dados_item['preco'])
                custo_ingredientes_total += custo_parcial
                lista_para_salvar.append({"nome_receita": nome_produto_final, "ingrediente": escolha, "qtd": qtd_usada, "unid": unid_uso})
                with c4:
                    st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra (%)", 0, 15, 2)
        perc_despesas = st.slider("Despesas Gerais (%)", 0, 100, 30)
        valor_embalagem = st.number_input("Embalagem (R$)", value=0.0)

    # --- CÁLCULOS ---
    v_quebra = custo_ingredientes_total * (perc_quebra / 100)
    v_despesas = custo_ingredientes_total * (perc_despesas / 100)
    custo_total_prod = custo_ingredientes_total + v_quebra + v_despesas + valor_embalagem
    preco_venda_final = custo_total_prod + (custo_total_prod * (margem_lucro / 100))

    # --- RESULTADO BOX ---
    st.markdown(f"""
        <div class='resultado-box'>
            <p>VALOR SUGERIDO</p>
            <h1>R$ {preco_venda_final:.2f}</h1>
        </div>
    """, unsafe_allow_html=True)

    # --- ORÇAMENTO (ESTRUTURA ORIGINAL SOLICITADA) ---
    st.divider()
    st.header("📋 Escolha a Receita Salva")
    
    # Campo de Seleção conforme Imagem
    receita_orc_sel = st.selectbox("Selecione a Receita para o Orçamento:", [""] + receitas_nomes, key="orc_receita_box")
    
    col_o1, col_o2, col_o3 = st.columns([2, 1, 1])
    with col_o1:
        prod_txt = st.text_input("Produto", value=receita_orc_sel)
    with col_o2:
        # Puxa o valor da planilha se a receita estiver lá
        p_unit_val = 0.0
        if receita_orc_sel == nome_produto_final:
            p_unit_val = preco_venda_final
        p_unit_orc = st.number_input("Preço Unitário (R$)", value=p_unit_val)
    with col_o3:
        qtd_orc = st.number_input("Quantidade", min_value=1, value=1, key="orc_qtd")

    # NOVOS BOTÕES: FRETE E EMBALAGEM NO ORÇAMENTO
    col_o4, col_o5, col_o6 = st.columns([1, 1, 1])
    with col_o4:
        frete_orc = st.number_input("Taxa de Entrega (R$)", value=0.0, key="orc_frete")
    with col_o5:
        emb_extra_orc = st.number_input("Embalagem Extra (R$)", value=0.0, key="orc_emb")
    with col_o6:
        st.write("")
        if st.button("➕ Adicionar", use_container_width=True):
            subtotal = (p_unit_orc * qtd_orc) + frete_orc + emb_extra_orc
            st.session_state.carrinho.append({
                "Produto": prod_txt,
                "Qtd": qtd_orc,
                "Preço Unit.": p_unit_orc,
                "Subtotal": subtotal
            })
            st.rerun()

    # Tabela Final e WhatsApp
    if st.session_state.carrinho:
        df_c = pd.DataFrame(st.session_state.carrinho)
        st.table(df_c)
        total_p = df_c["Subtotal"].sum()
        st.subheader(f"Total: R$ {total_p:.2f}")
        
        if st.button("Gerar orçamento para whatsapp"):
            itens = "".join([f"- {i['Produto']} ({i['Qtd']}x): R$ {i['Subtotal']:.2f}\n" for i in st.session_state.carrinho])
            st.code(f"Orçamento:\n{itens}\n*Total: R$ {total_p:.2f}*")

if __name__ == "__main__":
    main()
