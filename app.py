import streamlit as st
import pandas as pd

st.set_page_config(page_title="Precificador Pro - Doces", layout="wide")

# Estilização para o layout ficar profissional
st.markdown("""
    <style>
    .titulo-planilha { color: #1e3a8a; font-weight: bold; border-bottom: 2px solid #1e3a8a; margin-bottom: 20px; }
    .resultado-box { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #1e3a8a; }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.markdown("<h1 class='titulo-planilha'>OVO DE COLHER AO LEITE - SISTEMA DE PRECIFICAÇÃO</h1>", unsafe_allow_html=True)

    # 1. Base de Ingredientes (Simulada)
    if 'ingredientes' not in st.session_state:
        st.session_state.ingredientes = [
            {"nome": "Chocolate Sicao", "unidade": "kg", "preco": 65.00},
            {"nome": "Leite Condensado", "unidade": "unidade", "preco": 6.50},
            {"nome": "Creme de Leite", "unidade": "unidade", "preco": 4.20},
            {"nome": "Confeitos", "unidade": "g", "preco": 0.05}
        ]

    # --- ENTRADA DE DADOS ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📋 Composição da Receita")
        nome_prod = st.text_input("Nome do Produto", "Ovo de Colher Ao Leite")
        
        # Lista dinâmica de ingredientes
        n_ing = st.number_input("Quantos itens na receita?", min_value=1, value=3)
        custo_ingredientes_total = 0.0
        
        for i in range(int(n_ing)):
            c_a, c_b, c_c = st.columns([2, 1, 1])
            with c_a:
                nomes = [ing['nome'] for ing in st.session_state.ingredientes]
                item = st.selectbox(f"Ingrediente {i+1}", nomes, key=f"item_{i}")
            with c_b:
                qtd = st.number_input(f"Qtd", min_value=0.0, key=f"qtd_{i}")
            with c_c:
                unid = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"unid_{i}")
            
            # Cálculo lógico (Conversão g -> kg)
            base = next(x for x in st.session_state.ingredientes if x['nome'] == item)
            fator = 1.0
            if unid == "g" and base['unidade'] == "kg": fator = 1/1000
            elif unid == "kg" and base['unidade'] == "g": fator = 1000
            
            custo_ingredientes_total += (qtd * fator) * base['preco']

    with col2:
        st.subheader("📈 Custos Adicionais e Margens")
        quebra = st.slider("Quebra/Desperdício (%)", 0, 10, 5)
        despesas = st.slider("Despesas Gerais/Fixo (%)", 0, 50, 30)
        embalagem = st.number_input("Custo da Embalagem (R$)", min_value=0.0, value=8.67)
        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=150)

    # --- CÁLCULOS ESTILO PLANILHA (BASEADOS NA IMAGEM) ---
    # 1. Custo dos ingredientes + Quebra
    valor_quebra = custo_ingredientes_total * (quebra / 100)
    custo_com_quebra = custo_ingredientes_total + valor_quebra
    
    # 2. Despesas gerais sobre o custo base
    valor_despesas = custo_ingredientes_total * (despesas / 100)
    
    # 3. Custo total do produto (Ingredientes + Quebra + Despesas + Embalagem)
    custo_total_final = custo_com_quebra + valor_despesas + embalagem
    
    # 4. Lucro sobre o custo total
    valor_lucro = custo_total_final * (margem_lucro / 100)
    
    # 5. Preço de Venda
    preco_venda = custo_total_final + valor_lucro

    # --- EXIBIÇÃO FINAL ---
    st.divider()
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 📊 Resumo de Custos")
        resumo = {
            "Descrição": ["Custo Ingredientes", "Quebra (5%)", "Desp. Gerais (30%)", "Embalagem", "CUSTO TOTAL"],
            "Valores": [
                f"R$ {custo_ingredientes_total:.2f}",
                f"R$ {valor_quebra:.2f}",
                f"R$ {valor_despesas:.2f}",
                f"R$ {embalagem:.2f}",
                f"R$ {custo_total_final:.2f}"
            ]
        }
        st.table(pd.DataFrame(resumo))

    with c2:
        st.markdown("<div class='resultado-box'>", unsafe_allow_html=True)
        st.markdown(f"## PREÇO DE VENDA: R$ {preco_venda:.2f}")
        st.markdown(f"**Lucro Real:** R$ {valor_lucro:.2f}")
        st.markdown(f"**Margem Aplicada:** {margem_lucro}%")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.info(f"💡 Dica: Para vender o '{nome_prod}' com sucesso, seu custo de produção não deve ultrapassar 35% do preço de venda.")

if __name__ == "__main__":
    main()
