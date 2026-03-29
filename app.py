import streamlit as st
from ai_engine import structure_problem

st.set_page_config(page_title="Structured Execution AI")

st.title("🧠 Structured Execution AI")
st.write("Turn confusion into clarity")

# Input box
user_input = st.text_area("Describe your situation:")

# Button
if st.button("Structure It"):

    if user_input.strip() == "":
        st.warning("Please enter something")
    else:
        with st.spinner("Structuring..."):
            result = structure_problem(user_input)

        st.subheader("📊 Structured Output")
        st.text(result)