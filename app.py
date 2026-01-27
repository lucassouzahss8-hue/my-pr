import streamlit as st
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Precificador", layout="wide")

# Estilização CSS personalizada
st.markdown("""
    <style>
    /* Estilo do Título Principal */
    .titulo-planilha { 
        color: #1e3a8a; 
        font-weight: bold; 
        border-bottom: 2px solid #1e3a8a; 
        margin-bottom: 20px; 
    }
    
    /* QUADRADO DE RESULTADO - Agora em Cinza Escuro */
    .resultado-box { 
        background-color: #262730; /* Cinza Escuro */
        padding: 25px; 
        border-radius: 15px; 
        border-left: 10px solid #1e3a8a; /* Detalhe lateral azul */
        box-shadow: 2px 2px 15px rgba(0,0,0,0.3); 
        color: #ffffff; /* Texto em Branco para leitura */
    }
    
    /* Estilo das tabelas para combinar */
    .stTable { 
        background-color: #ffffff; 
        border-radius: 10px; 
    }
    </style>
    """, unsafe_allow_html=True)

# Função para carregar o banco de dados
def carregar_banco():
    try:
        df = pd.read_csv("ingredientes.csv")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception:
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

def main():
    df_db = carregar_banco()

    # Título
    st.markdown("<h1 class='titulo-planilha'>Precificador</h1>", unsafe_allow_html=True)

    # --- SEÇÃO DO PRODUTO ---
    col_prod1, col_prod2 = st.columns([2, 1])
    
    with col_prod1:
        nome_produto_final = st.text_input("Nome do Produto Final:", value="", placeholder="Ex: Bolo de Chocolate")
    
    with col_prod2:
        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=150)

    st.divider()

    if df_db.empty:
        st.error("⚠️ Arquivo 'ingredientes.csv' não encontrado no GitHub.")
        return

    # --- MONTAGEM DA RECEITA ---
    col_esq, col_dir = st.columns([2, 1])

    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens = st.number_input("Quantidade de itens na receita:", min_value=1, max_value=50, value=1)
        
        custo_ingredientes_total = 0.0

        for i in range(int(n_itens)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            
            with c1:
                escolha = st.selectbox(f"Item {i+1}", options=df_db['nome'].tolist(), key=f"nome_{i}")
            
            dados_item = df_db[df_db['nome'] == escolha].iloc[0]
            unid_base = str(dados_item['unidade']).lower().strip()
            preco_base = float(dados_item['preco'])

            with c2:
                qtd_usada = st.number_input(f"Qtd", min_value=0.0, key=f"qtd_{i}", step=0.01)
            
            with c3:
                unid_uso = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")

            # Lógica de Conversão
            fator = 1.0
            if unid_uso == "g" and unid_base == "kg": fator = 1/1000
            elif unid_uso == "kg" and unid_base == "g": fator = 1000
            elif unid_uso.lower() == "ml" and unid_base.lower() == "l": fator = 1/1000
            elif unid_uso.lower() == "l" and unid_base.lower() == "ml": fator = 1000
            
            custo_parcial = (qtd_usada * fator) * preco_base
            custo_ingredientes_total += custo_parcial

            with c4:
                st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    # --- ADICIONAIS ---
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
    preco_final = custo_total_prod + lucro_valor

    # --- EXIBIÇÃO ---
    st.divider()
    res1, res2 = st.columns([1.5, 1])

    with res1:
        st.markdown(f"### Detalhamento: {nome_produto_final if nome_produto_final else 'Novo Produto'}")
        df_resumo = pd.DataFrame({
            "Item": ["Ingredientes", "Quebra", "Despesas", "Embalagem", "TOTAL CUSTO"],
            "Valor": [f"R$ {custo_ingredientes_total:.2f}", f"R$ {v_quebra:.2f}", f"R$ {v_despesas:.2f}", f"R$ {valor_embalagem:.2f}", f"R$ {custo_total_prod:.2f}"]
        })
        st.table(df_resumo)

    with res2:
        # Exibição no quadrado cinza escuro
        st.markdown(f"""
        <div class='resultado-box'>
            <p style='margin:0; font-size:14px; color: #a1a1aa;'>PRODUTO: {nome_produto_final.upper() if nome_produto_final else '---'}</p>
            <h2 style='margin:0; color: #ffffff;'>PREÇO DE VENDA</h2>
            <h1 style='color:#60a5fa; font-size:48px;'>R$ {preco_final:.2f}</h1>
            <hr style='border-color: #4b5563;'>
            <p><b>Lucro Real:</b> <span style='color: #4ade80;'>R$ {lucro_valor:.2f}</span></p>
            <p><b>Margem:</b> {margem_lucro}%</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
