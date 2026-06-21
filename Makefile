.PHONY: install run

install:
	pip install -r pptx_studio/requirements.txt

run:
	streamlit run pptx_studio/app.py
