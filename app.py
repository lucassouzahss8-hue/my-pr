import streamlit as st
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Precificador Pro - Doces & Salgados", layout="wide")

# Estilização CSS para visual Profissional
st.markdown("""
    <style>
    .titulo-planilha { color: #1e3a8a; font-weight: bold; border-bottom: 2px solid #1e3a8a; margin-bottom: 20px; }
    .resultado-box { background-color: #f0f2f6; padding: 25px; border-radius: 15px; border-left: 10px solid #1e3a8a; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }
    .stTable { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 1. FUNÇÃO PARA CARREGAR O BANCO DE DADOS (CSV)
def carregar_banco():
    try:
        # Lê o arquivo CSV que você subiu no GitHub
        df = pd.read_csv("ingredientes.csv")
        # Garante que as colunas estejam limpas
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        # Caso o arquivo não exista ou esteja errado, mostra um aviso e usa um padrão
        st.error(f"Erro ao carregar 'ingredientes.csv': {e}")
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

def main():
    st.markdown("<h1 class='titulo-planilha'>SISTEMA DE PRECIFICAÇÃO PROFISSIONAL</h1>", unsafe_allow_html=True)

    # Carregar dados do CSV para a sessão
    df_db = carregar_banco()

    if df_db.empty:
        st.warning("⚠️ O arquivo 'ingredientes.csv' está vazio ou não foi encontrado no GitHub.")
        return

    # --- ENTRADA DE DADOS PRINCIPAIS ---
    col_header1, col_header2 = st.columns([2, 1])
    
    with col_header1:
        nome_produto = st.text_input("Nome do Produto Final", "Ovo de Colher Ao Leite")
    with col_header2:
        margem_lucro = st.number_input("Margem de Lucro Desejada (%)", min_value=0, value=150)

    st.divider()

    # --- MONTAGEM DA RECEITA ---
    col_esq, col_dir = st.columns([2, 1])

    with col_esq:
        st.subheader("📋 Ingredientes e Quantidades")
        
        # Seleção de quantos ingredientes compõem este produto
        n_itens = st.number_input("Quantos ingredientes nesta receita?", min_value=1, max_value=30, value=3)
        
        itens_selecionados = []
        custo_ingredientes_total = 0.0

        # Criando a grade de entrada
        for i in range(int(n_itens)):
            c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 2])
            
            with c1:
                escolha = st.selectbox(f"Item {i+1}", options=df_db['nome'].tolist(), key=f"nome_{i}")
            
            # Busca dados do item no banco carregado
            dados_item = df_db[df_db['nome'] == escolha].iloc[0]
            unid_base = str(dados_item['unidade']).lower().strip()
            preco_base = float(dados_item['preco'])

            with c2:
                qtd_usada = st.number_input(f"Qtd.", min_value=0.0, step=0.01, key=f"qtd_{i}")
            
            with c3:
                unid_uso = st.selectbox(f"Unid.", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")

            # LÓGICA DE CONVERSÃO DE UNIDADES
            fator = 1.0
            if unid_uso == "g" and unid_base == "kg": fator = 1/1000
            elif unid_uso == "kg" and unid_base == "g": fator = 1000
            elif unid_uso == "ml" and unid_base == "l": fator = 1/1000
            elif unid_uso == "L" and unid_base == "ml": fator = 1000
            
            custo_parcial = (qtd_usada * fator) * preco_base
            custo_ingredientes_total += custo_parcial

            with c4:
                st.markdown(f"<p style='padding-top:35px;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    # --- CUSTOS ADICIONAIS (ESTILO PLANILHA) ---
    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra/Desperdício (%)", 0, 20, 5)
        perc_despesas = st.slider("Despesas Gerais (%)", 0, 100, 30)
        valor_embalagem = st.number_input("Custo de Embalagem (R$)", min_value=0.0, value=8.67)

    # --- CÁLCULOS FINAIS ---
    valor_quebra = custo_ingredientes_total * (perc_quebra / 100)
    valor_despesas = custo_ingredientes_total * (perc_despesas / 100)
    
    # Custo Total = Ingredientes + Quebra + Despesas + Embalagem
    custo_producao_total = custo_ingredientes_total + valor_quebra + valor_despesas + valor_embalagem
    
    lucro_real = custo_producao_total * (margem_lucro / 100)
    preco_venda_final = custo_producao_total + lucro_real

    # --- EXIBIÇÃO DO RESULTADO ESTILO PLANILHA ---
    st.divider()
    
    res_col1, res_col2 = st.columns([1.5, 1])

    with res_col1:
        st.markdown("### 📝 Resumo da Planilha")
        tabela_final = pd.DataFrame({
            "Descrição": ["Total Ingredientes", "Quebra/Desperdício", "Despesas Gerais", "Embalagem", "CUSTO TOTAL"],
            "Cálculo": ["Soma dos itens", f"{perc_quebra}% s/ ingredientes", f"{perc_despesas}% s/ ingredientes", "Valor fixo", "Custo de Produção"],
            "Valor": [
                f"R$ {custo_ingredientes_total:.2f}",
                f"R$ {valor_quebra:.2f}",
                f"R$ {valor_despesas:.2f}",
                f"R$ {valor_embalagem:.2f}",
                f"R$ {custo_producao_total:.2f}"
            ]
        })
        st.table(tabela_final)

    with res_col2:
        st.markdown(f"""
        <div class='resultado-box'>
            <h2 style='margin-top:0;'>PREÇO DE VENDA</h2>
            <h1 style='color:#1e3a8a;'>R$ {preco_venda_final:.2f}</h1>
            <hr>
            <p><b>Produto:</b> {nome_produto}</p>
            <p><b>Margem de Lucro:</b> {margem_lucro}%</p>
            <p><b>Lucro no Bolso:</b> R$ {lucro_real:.2f}</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
