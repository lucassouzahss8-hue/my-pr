import streamlit as st
import pandas as pd
import os

# Configuração da Página
st.set_page_config(page_title="Precificador", layout="wide")

# Estilização CSS
st.markdown("""
    <style>
    .titulo-planilha { color: #1e3a8a; font-weight: bold; border-bottom: 2px solid #1e3a8a; margin-bottom: 20px; }
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

# Inicialização do Estado
if "n_itens" not in st.session_state:
    st.session_state.n_itens = 1
if "nome_prod" not in st.session_state:
    st.session_state.nome_prod = ""

# --- FUNÇÕES DE BANCO DE DADOS ---
def carregar_ingredientes():
    try:
        df = pd.read_csv("ingredientes.csv")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

def carregar_receitas():
    if os.path.exists("receitas_salvas.csv"):
        return pd.read_csv("receitas_salvas.csv")
    return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

def salvar_receita_csv(nome, lista_itens):
    df_nova = pd.DataFrame(lista_itens)
    df_nova['nome_receita'] = nome
    if os.path.exists("receitas_salvas.csv"):
        df_antiga = pd.read_csv("receitas_salvas.csv")
        df_antiga = df_antiga[df_antiga['nome_receita'] != nome]
        df_final = pd.concat([df_antiga, df_nova], ignore_index=True)
    else:
        df_final = df_nova
    df_final.to_csv("receitas_salvas.csv", index=False)

def deletar_receita_csv(nome):
    if os.path.exists("receitas_salvas.csv"):
        df = pd.read_csv("receitas_salvas.csv")
        df_restante = df[df['nome_receita'] != nome]
        df_restante.to_csv("receitas_salvas.csv", index=False)
        return True
    return False

def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas()

    st.markdown("<h1 class='titulo-planilha'>Precificador</h1>", unsafe_allow_html=True)

    # --- GERENCIAR RECEITAS ---
    with st.expander("📂 Gerenciar Receitas Salvas"):
        receitas_nomes = df_rec['nome_receita'].unique().tolist()
        col_rec1, col_rec2 = st.columns([3, 1])
        with col_rec1:
            receita_selecionada = st.selectbox("Selecione uma receita:", [""] + receitas_nomes)
        with col_rec2:
            st.write("") 
            st.write("") 
            if st.button("Carregar Dados", use_container_width=True):
                if receita_selecionada != "":
                    dados_rec = df_rec[df_rec['nome_receita'] == receita_selecionada]
                    st.session_state.nome_prod = receita_selecionada
                    st.session_state.n_itens = len(dados_rec)
                    for idx, row in enumerate(dados_rec.itertuples()):
                        st.session_state[f"nome_{idx}"] = row.ingrediente
                        st.session_state[f"qtd_{idx}"] = float(row.qtd)
                        st.session_state[f"u_{idx}"] = row.unid
                    st.rerun()
            if st.button("🗑️ Deletar Receita", use_container_width=True):
                if receita_selecionada != "":
                    deletar_receita_csv(receita_selecionada)
                    st.rerun()

    # --- SEÇÃO DO PRODUTO E ENTREGA ---
    col_prod1, col_prod2, col_prod3 = st.columns([2, 1, 1])
    with col_prod1:
        nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod", placeholder="Ex: Bolo de Chocolate")
    with col_prod2:
        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=150)
    with col_prod3:
        # NOVO CAMPO: TAXA DE ENTREGA
        taxa_entrega = st.number_input("Taxa de Entrega (R$)", min_value=0.0, value=0.0, step=1.0, help="Deixe 0 se a entrega for grátis até 5km.")

    st.divider()

    if df_ing.empty:
        st.error("⚠️ Arquivo 'ingredientes.csv' não encontrado.")
        return

    # --- MONTAGEM DA RECEITA ---
    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens = st.number_input("Quantidade de itens na receita:", min_value=1, key="n_itens")
        custo_ingredientes_total = 0.0
        lista_para_salvar = []

        for i in range(int(n_itens)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                default_index = 0
                if f"nome_{i}" in st.session_state:
                    try: default_index = df_ing['nome'].tolist().index(st.session_state[f"nome_{i}"])
                    except: pass
                escolha = st.selectbox(f"Item {i+1}", options=df_ing['nome'].tolist(), key=f"nome_{i}", index=default_index)
            
            dados_item = df_ing[df_ing['nome'] == escolha].iloc[0]
            unid_base = str(dados_item['unidade']).lower().strip()
            preco_base = float(dados_item['preco'])

            with c2:
                qtd_usada = st.number_input(f"Qtd", min_value=0.0, key=f"qtd_{i}", step=0.01)
            with c3:
                unid_uso = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")

            fator = 1.0
            if unid_uso == "g" and unid_base == "kg": fator = 1/1000
            elif unid_uso == "kg" and unid_base == "g": fator = 1000
            elif unid_uso.lower() == "ml" and unid_base.lower() == "l": fator = 1/1000
            elif unid_uso.lower() == "l" and unid_base.lower() == "ml": fator = 1000
            
            custo_parcial = (qtd_usada * fator) * preco_base
            custo_ingredientes_total += custo_parcial
            lista_para_salvar.append({"ingrediente": escolha, "qtd": qtd_usada, "unid": unid_uso})
            with c4:
                st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra (%)", 0, 15, 5)
        perc_despesas = st.slider("Despesas Gerais (%)", 0, 100, 30)
        valor_embalagem = st.number_input("Embalagem (R$)", min_value=0.0, value=0.0, step=0.1)

    # --- CÁLCULOS ---
    v_quebra = custo_ingredientes_total * (perc_quebra / 100)
    v_despesas = custo_ingredientes_total * (perc_despesas / 100)
    custo_total_prod = custo_ingredientes_total + v_quebra + v_despesas + valor_embalagem
    lucro_valor = custo_total_prod * (margem_lucro / 100)
    
    # Preço de Venda inclui o Produto + a Entrega
    preco_venda_produto = custo_total_prod + lucro_valor
    preco_venda_final_com_entrega = preco_venda_produto + taxa_entrega

    # --- EXIBIÇÃO ---
    st.divider()
    res1, res2 = st.columns([1.5, 1])
    with res1:
        st.markdown(f"### Detalhamento: {nome_produto_final if nome_produto_final else 'Novo Produto'}")
        df_resumo = pd.DataFrame({
            "Item": ["Produção", "Lucro", "Taxa de Entrega", "VALOR TOTAL A COBRAR"],
            "Valor": [
                f"R$ {custo_total_prod:.2f}", 
                f"R$ {lucro_valor:.2f}", 
                f"R$ {taxa_entrega:.2f}", 
                f"R$ {preco_venda_final_com_entrega:.2f}"
            ]
        })
        st.table(df_resumo)
        if st.button("💾 Salvar esta Receita"):
            if nome_produto_final:
                salvar_receita_csv(nome_produto_final, lista_para_salvar)
                st.success("Salva!")
                st.rerun()

    with res2:
        st.markdown(f"""
        <div class='resultado-box'>
            <p style='margin:0; font-size:14px; opacity: 0.8;'>PRODUTO: {nome_produto_final.upper() if nome_produto_final else '---'}</p>
            <h2 style='margin:0;'>TOTAL PARA O CLIENTE</h2>
            <h1 style='color: #60a5fa !important; font-size:48px;'>R$ {preco_venda_final_com_entrega:.2f}</h1>
            <hr style='border-color: #4b5563;'>
            <p><b>Preço do Produto:</b> R$ {preco_venda_produto:.2f}</p>
            <p><b>Taxa de Entrega:</b> R$ {taxa_entrega:.2f}</p>
            <p><b>Seu Lucro Líquido:</b> <span style='color: #4ade80;'>R$ {lucro_valor:.2f}</span></p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
