# Claims Prediction MLOps

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![MLflow](https://img.shields.io/badge/MLflow-+-blue)](https://mlflow.org/)
[![DVC](https://img.shields.io/badge/DVC-Data%20Version%20Control-9cf)](https://dvc.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Container-2496ED)](https://www.docker.com/)

## Contexto del Proyecto (El "Por qué")

Este repositorio no es un simple notebook de Kaggle. Es un proyecto de **MLOps de principio a fin** diseñado para demostrar las mejores prácticas en un entorno altamente regulado, como el sector de **Banca y Seguros**.

El objetivo es construir un sistema de predicción de severidad de reclamaciones de seguros de auto que no solo sea preciso, sino también **auditable, reproducible y desplegable en producción** con un solo comando.

## Metodología y Estructura

La arquitectura del proyecto sigue los principios de [Cookiecutter Data Science](https://drivendata.github.io/cookiecutter-data-science/) y prácticas de MLOps para garantizar la separación de concerns y la reproducibilidad.


├── .github/workflows # CI/CD Pipelines (GitHub Actions)
├── config # Ficheros de configuración (YAML)
├── data
│ ├── raw # Datos inmutables. ¡NO EDITAR MANUALMENTE!
│ ├── interim # Datos transformados intermedios
│ └── processed # Datos listos para el modelado (feature store)
├── models # Modelos entrenados, serializados (pickle, ONNX)
├── notebooks # EDA y experimentación inicial (numerados: 1.0-...)
├── reports # Análisis generados (métricas, figuras, SHAP)
│ └── figures
├── src # Código fuente modular (pip install -e .)
│ ├── data # Scripts de ingesta y limpieza
│ ├── features # Scripts de feature engineering
│ ├── models # Scripts de entrenamiento, predicción y scoring
│ └── visualization # Scripts de visualización (EDA, resultados)
├── tests # Tests unitarios y de integración
├── .dvc # Configuración de DVC (Data Version Control)
├── Dockerfile # Contenedor para el servicio de inferencia (API)
├── requirements.txt # Dependencias del proyecto
└── Makefile # Automatización de tareas (setup, test, run)


## Stack Tecnológico

- **Control de Versiones:** Git + DVC (para datos y modelos)
- **Experimentación:** Jupyter, MLflow Tracking
- **Modelado:** Scikit-learn, XGBoost
- **Explicabilidad:** SHAP
- **API:** FastAPI
- **Contenedorización:** Docker
- **CI/CD:** GitHub Actions
- **Despliegue:** Cloud (Render/AWS/GCP)

