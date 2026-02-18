#!/usr/bin/env python
# src/data_generation/generate_claims_data.py

"""
Generador de datos sintéticos para reclamaciones de seguros de auto.
Simula un entorno realista con correlaciones de negocio y patrones de fraude.
"""

import numpy as np
import pandas as pd
import yaml
from pathlib import Path
import logging
from datetime import datetime, timedelta
from faker import Faker
import random
from typing import Dict, Any, List

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class InsuranceClaimsGenerator:
    """
    Generador de datos sintéticos con realismo de negocio asegurador.
    """
    
    def __init__(self, config_path: str = "config/data_generation.yaml"):
        """
        Inicializa el generador con la configuración.
        
        Args:
            config_path: Ruta al archivo de configuración YAML
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Semilla para reproducibilidad
        np.random.seed(self.config.get('random_seed', 42))
        random.seed(self.config.get('random_seed', 42))
        Faker.seed(self.config.get('random_seed', 42))
        
        # Inicializar Faker para datos localizados (USA, por ser común en seguros)
        self.fake = Faker('en_US')
        
        # Almacenar datos generados para consistencia (ej. un policyholder puede tener múltiples claims)
        self.policyholders = {}
        self.policies = {}
        
        logging.info("Generador de datos de reclamaciones inicializado")
        logging.info(f"Objetivo: {self.config['output']['n_samples']} registros")
    
    def _generate_policyholder(self, policyholder_id: str) -> Dict[str, Any]:
        """
        Genera un asegurado (policyholder) con características coherentes.
        """
        age = int(np.random.normal(
            self.config['policyholder']['age_distribution']['mean'],
            self.config['policyholder']['age_distribution']['std']
        ))
        age = np.clip(age, 
                     self.config['policyholder']['age_distribution']['min'],
                     self.config['policyholder']['age_distribution']['max'])
        
        sex = np.random.choice(
            list(self.config['policyholder']['sex_distribution'].keys()),
            p=list(self.config['policyholder']['sex_distribution'].values())
        )
        
        education = np.random.choice(
            self.config['policyholder']['education_levels'],
            p=self.config['policyholder']['education_weights']
        )
        
        # Ingreso correlacionado con educación y edad (mayor edad/educación → mayor ingreso)
        income_base = np.random.normal(
            self.config['policyholder']['income_distribution']['mean'],
            self.config['policyholder']['income_distribution']['std']
        )
        
        # Ajustes por edad y educación
        age_factor = 1.0 + (age - 45) / 100  # Jóvenes y viejos ganan menos (forma de U invertida)
        edu_factor = {
            'No Education': 0.6,
            'High School': 0.8,
            'Bachelor': 1.0,
            'Master': 1.3,
            'PhD': 1.5
        }[education]
        
        income = int(income_base * age_factor * edu_factor)
        income = np.clip(income,
                        self.config['policyholder']['income_distribution']['min'],
                        self.config['policyholder']['income_distribution']['max'])
        
        # Fecha de nacimiento coherente con edad
        birth_date = datetime.now() - timedelta(days=int(age * 365))
        
        policyholder = {
            'policyholder_id': policyholder_id,
            'age': age,
            'sex': sex,
            'education_level': education,
            'income': income,
            'birth_date': birth_date.strftime('%Y-%m-%d'),
            'has_previous_claims': np.random.choice([True, False], p=[0.3, 0.7]),  # 30% ha reclamado antes
            'years_as_customer': max(1, int(age - 25 + np.random.randint(-5, 5)))  # Clientes desde ~25 años
        }
        
        return policyholder
    
    def _generate_vehicle(self, policyholder: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un vehículo coherente con el asegurado.
        El tipo de vehículo se correlaciona con ingresos y edad.
        """
        # Edad del vehículo (distribución exponencial: más vehículos nuevos que viejos)
        lambda_param = self.config['vehicle']['age_distribution']['lambda']
        vehicle_age = int(np.random.exponential(1/lambda_param))
        vehicle_age = min(vehicle_age, self.config['vehicle']['age_distribution']['max'])
        
        # Marca del vehículo influenciada por ingresos
        # Las marcas de lujo son más probables con ingresos altos
        base_makes = self.config['vehicle']['makes']
        base_weights = np.array(self.config['vehicle']['make_weights'], dtype=float)
        
        # Ajustar pesos por ingresos
        income = policyholder['income']
        luxury_indices = [5, 6, 7]  # BMW, Mercedes, Audi
        if income > 80000:
            # Aumentar probabilidad de marcas de lujo
            for idx in luxury_indices:
                if idx < len(base_weights):
                    base_weights[idx] *= 2
        elif income < 30000:
            # Disminuir probabilidad de marcas de lujo
            for idx in luxury_indices:
                if idx < len(base_weights):
                    base_weights[idx] *= 0.3
        
        # Re-normalizar
        base_weights = base_weights / base_weights.sum()
        
        vehicle_make = np.random.choice(base_makes, p=base_weights)
        
        # Precio base del vehículo según marca
        base_prices = {
            'Toyota': 25000, 'Honda': 26000, 'Ford': 28000, 'Chevrolet': 27000,
            'Nissan': 24000, 'BMW': 45000, 'Mercedes': 50000, 'Audi': 48000,
            'Hyundai': 22000, 'Kia': 21000
        }
        
        # Precio actual depreciado por edad
        # CORRECCIÓN: Manejo robusto de price_multipliers
        price_multipliers = self.config['vehicle']['price_multiplier_by_age']
        
        try:
            # Convertir las claves a enteros para facilitar la comparación
            price_multipliers_int = {}
            for k, v in price_multipliers.items():
                try:
                    # Intentar convertir la clave a entero
                    price_multipliers_int[int(k)] = v
                except (ValueError, TypeError):
                    # Si no se puede convertir, usar la clave original
                    logging.warning(f"Clave no numérica en price_multipliers: {k}")
                    price_multipliers_int[k] = v
            
            # Obtener las edades numéricas ordenadas
            ages = sorted([k for k in price_multipliers_int.keys() if isinstance(k, (int, float))])
            
            # Encontrar el multiplicador correspondiente
            multiplier = 1.0
            for a in ages:
                if vehicle_age <= a:
                    multiplier = price_multipliers_int[a]
                    break
            else:
                # Si no se encontró, usar el último valor disponible
                if ages:
                    multiplier = price_multipliers_int[ages[-1]]
                else:
                    # Si no hay edades numéricas, usar el primer valor disponible
                    multiplier = list(price_multipliers_int.values())[0] if price_multipliers_int else 0.7
                    
        except Exception as e:
            logging.error(f"Error al procesar price_multipliers: {e}")
            # Valor por defecto en caso de error
            multiplier = 0.7
        
        # Calcular precio del vehículo
        vehicle_price = int(base_prices.get(vehicle_make, 25000) * multiplier)
        
        vehicle = {
            'vehicle_make': vehicle_make,
            'vehicle_age': vehicle_age,
            'vehicle_price': vehicle_price,
            'vehicle_model': self.fake.word().capitalize(),  # Modelo aleatorio
            'vehicle_year': datetime.now().year - vehicle_age
        }
        
        return vehicle
    
    def _generate_incident(self, policyholder: Dict[str, Any], vehicle: Dict[str, Any], 
                          incident_date: datetime) -> Dict[str, Any]:
        """
        Genera un incidente (siniestro) con características realistas.
        La severidad y tipo se correlacionan con factores del vehículo y asegurado.
        """
        # Tipo de incidente
        incident_types = self.config['incident']['types']
        type_weights = np.array(self.config['incident']['type_weights'], dtype=float)
        
        # Ajustar pesos por condiciones (ej. coches viejos más propensos a colisiones simples?)
        if vehicle['vehicle_age'] > 15:
            # Aumentar probabilidad de "Single Vehicle Collision" (fallo mecánico)
            if len(type_weights) > 0:
                type_weights[0] *= 1.5
        
        type_weights = type_weights / type_weights.sum()
        incident_type = np.random.choice(incident_types, p=type_weights)
        
        # Severidad del incidente
        severities = self.config['incident']['severity_levels']
        severity_weights = np.array(self.config['incident']['severity_weights'], dtype=float)
        
        # La severidad aumenta con la velocidad (simulada por hora del día, etc.)
        hour = incident_date.hour
        if 0 <= hour <= 5:  # Madrugada, más probabilidad de accidentes graves (velocidad, alcohol)
            severity_weights = severity_weights * np.array([0.8, 1.0, 1.5, 2.0])
        elif 17 <= hour <= 20:  # Hora punta, más colisiones menores
            severity_weights = severity_weights * np.array([1.5, 1.2, 0.8, 0.5])
        
        severity_weights = severity_weights / severity_weights.sum()
        incident_severity = np.random.choice(severities, p=severity_weights)
        
        # Autoridades contactadas
        authorities = self.config['incident']['authorities_contacted']
        authorities_weights = np.array(self.config['incident']['authorities_weights'], dtype=float)
        
        # Ajustar por severidad
        if incident_severity in ['Major Damage', 'Total Loss']:
            authorities_weights[3] *= 0.1  # Mucho menos probable "None"
            authorities_weights[0] *= 1.5  # Más probable "Police"
        
        authorities_weights = authorities_weights / authorities_weights.sum()
        authorities_contacted = np.random.choice(authorities, p=authorities_weights)
        
        # Número de testigos
        if incident_severity in ['Major Damage', 'Total Loss']:
            witnesses = int(np.random.poisson(lam=3))
        else:
            witnesses = int(np.random.poisson(lam=1))
        witnesses = min(witnesses, 5)
        
        # Número de vehículos involucrados según tipo
        if 'Multi-vehicle' in incident_type:
            vehicles_involved = int(np.random.randint(2, 5))
        elif 'Single' in incident_type or 'Parked' in incident_type:
            vehicles_involved = 1
        else:
            vehicles_involved = int(np.random.randint(1, 3))
        
        incident = {
            'incident_type': incident_type,
            'incident_severity': incident_severity,
            'authorities_contacted': authorities_contacted,
            'witnesses': witnesses,
            'number_of_vehicles_involved': vehicles_involved,
            'incident_hour': hour,
            'incident_day_of_week': incident_date.weekday(),
            'is_weekend': incident_date.weekday() >= 5,
            'incident_month': incident_date.month,
            'incident_date': incident_date.strftime('%Y-%m-%d')
        }
        
        return incident
    
    def _generate_claim_amounts(self, vehicle: Dict[str, Any], incident: Dict[str, Any], 
                                policyholder: Dict[str, Any], is_fraud: bool) -> Dict[str, float]:
        """
        Genera los montos de reclamación (injury, property, vehicle) con realismo.
        El fraude infla los montos.
        """
        # Monto base es un porcentaje del valor del vehículo, más aleatoriedad
        vehicle_value = vehicle['vehicle_price']
        
        # Porcentaje dañado según severidad
        severity_pct = {
            'Minor Damage': (0.01, 0.10),
            'Moderate Damage': (0.10, 0.30),
            'Major Damage': (0.30, 0.60),
            'Total Loss': (0.80, 1.0)
        }[incident['incident_severity']]
        
        vehicle_claim = int(vehicle_value * np.random.uniform(*severity_pct))
        
        # Reclamación de propiedad (daños a terceros, objetos)
        if 'Multi-vehicle' in incident['incident_type']:
            property_claim = int(vehicle_value * 0.3 * np.random.uniform(0.5, 1.5))
        else:
            property_claim = int(vehicle_value * 0.1 * np.random.uniform(0, 1))
        
        # Reclamación por lesiones
        if incident['incident_severity'] in ['Major Damage', 'Total Loss']:
            injury_claim = int(np.random.uniform(5000, 50000))
        elif 'injury' in incident['incident_type'].lower():
            injury_claim = int(np.random.uniform(1000, 20000))
        else:
            injury_claim = int(np.random.exponential(scale=2000))
            injury_claim = min(injury_claim, 10000)
        
        # Si es fraude, inflar los montos (especialmente injury y vehicle)
        if is_fraud:
            vehicle_claim = int(vehicle_claim * np.random.uniform(1.5, 3.0))
            property_claim = int(property_claim * np.random.uniform(1.2, 2.5))
            injury_claim = int(injury_claim * np.random.uniform(2.0, 4.0))
        
        # Limitar a máximos realistas
        vehicle_claim = min(vehicle_claim, vehicle_value * 2)  # No más del doble del valor
        property_claim = min(property_claim, 100000)
        injury_claim = min(injury_claim, 200000)
        
        return {
            'vehicle_claim': vehicle_claim,
            'property_claim': property_claim,
            'injury_claim': injury_claim
        }
    
    def _determine_fraud(self, policyholder: Dict[str, Any], vehicle: Dict[str, Any],
                        incident: Dict[str, Any], claim_amounts: Dict[str, float]) -> bool:
        """
        Determina si una reclamación es fraudulenta basándose en múltiples factores de riesgo.
        Este es el corazón del modelo de negocio.
        """
        base_rate = self.config['fraud']['base_rate']
        
        # Calcular odds iniciales
        odds = base_rate / (1 - base_rate)
        
        # Aplicar multiplicadores de riesgo
        multipliers = self.config['fraud']['multipliers']
        
        # Monto alto
        total_claim = sum(claim_amounts.values())
        if total_claim > 20000:
            odds *= multipliers['high_claim_amount']
        
        # Coche viejo
        if vehicle['vehicle_age'] > 10:
            odds *= multipliers['old_car']
        
        # No contactaron autoridades
        if incident['authorities_contacted'] == 'None':
            odds *= multipliers['no_authorities']
        
        # Fin de semana
        if incident['is_weekend']:
            odds *= multipliers['weekend_incident']
        
        # Madrugada
        if 0 <= incident['incident_hour'] <= 5:
            odds *= multipliers['late_night']
        
        # Hay reclamación por lesiones
        if claim_amounts['injury_claim'] > 0:
            odds *= multipliers['injury_claim']
        
        # Historial previo (proxy: el asegurado ha tenido reclamaciones antes)
        if policyholder['has_previous_claims']:
            odds *= multipliers.get('previous_claims', 1.3)
        
        # Convertir odds a probabilidad
        probability = odds / (1 + odds)
        
        # Asegurar que no se descontrole
        probability = min(probability, 0.95)
        
        return np.random.random() < probability
    
    def generate_dataset(self) -> pd.DataFrame:
        """
        Genera el dataset completo de reclamaciones.
        """
        n_samples = self.config['output']['n_samples']
        start_date = datetime.strptime(self.config['temporal']['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(self.config['temporal']['end_date'], '%Y-%m-%d')
        
        data = []
        
        logging.info(f"Generando {n_samples} registros...")
        
        for i in range(n_samples):
            if (i + 1) % 10000 == 0:
                logging.info(f"Progreso: {i + 1}/{n_samples} registros")
            
            # ID único para la reclamación
            claim_id = f"CLM{str(i+1).zfill(8)}"
            
            # Policyholder (podría ser recurrente, pero por simplicidad generamos nuevo cada claim)
            # En un escenario más realista, un policyholder podría tener múltiples claims
            policyholder_id = f"PH{str(np.random.randint(1, n_samples//10)).zfill(6)}"
            
            if policyholder_id not in self.policyholders:
                self.policyholders[policyholder_id] = self._generate_policyholder(policyholder_id)
            
            policyholder = self.policyholders[policyholder_id]
            
            # Generar vehículo (también podría ser persistente)
            vehicle = self._generate_vehicle(policyholder)
            
            # Fecha del incidente (distribución uniforme, pero con posible estacionalidad)
            days_range = (end_date - start_date).days
            random_days = np.random.randint(0, days_range)
            incident_date = start_date + timedelta(days=int(random_days))
            
            # Aplicar estacionalidad si está configurada (más accidentes en invierno)
            if self.config['temporal'].get('seasonality_effect', False):
                month = incident_date.month
                if month in [12, 1, 2]:  # Invierno
                    # 20% más probable
                    if np.random.random() > 0.8:
                        # Ajustar fecha para que sea en invierno (reescoger)
                        winter_days = [date for date in [start_date + timedelta(days=d) 
                                                         for d in range(days_range)] 
                                      if date.month in [12, 1, 2]]
                        if winter_days:
                            incident_date = np.random.choice(winter_days)
            
            # Generar incidente
            incident = self._generate_incident(policyholder, vehicle, incident_date)
            
            # Determinar si es fraude (antes de montos, porque los montos se ajustan si es fraude)
            # Pero necesitamos montos para calcular fraude... hay interdependencia.
            # Solución: estimar montos base, decidir fraude, re-calibrar montos si fraude.
            temp_claim_amounts = self._generate_claim_amounts(vehicle, incident, policyholder, is_fraud=False)
            is_fraud = self._determine_fraud(policyholder, vehicle, incident, temp_claim_amounts)
            
            # Generar montos finales (con posible inflación por fraude)
            claim_amounts = self._generate_claim_amounts(vehicle, incident, policyholder, is_fraud)
            
            # Estado del incidente (geografía)
            incident_state = self.fake.state_abbr()
            policy_state = incident_state  # Por simplicidad, misma estado
            
            # Construir registro completo
            record = {
                'claim_id': claim_id,
                'policyholder_id': policyholder_id,
                **{f'policyholder_{k}': v for k, v in policyholder.items() if k != 'policyholder_id'},
                **{f'vehicle_{k}': v for k, v in vehicle.items()},
                **incident,
                **claim_amounts,
                'total_claim_amount': sum(claim_amounts.values()),
                'policy_state': policy_state,
                'incident_state': incident_state,
                'fraud_reported': 'Y' if is_fraud else 'N',
                'policy_tenure': policyholder['years_as_customer'] * 365,  # en días
                'policy_bind_date': (incident_date - timedelta(days=policyholder['years_as_customer']*365)).strftime('%Y-%m-%d')
            }
            
            # Limpiar campos que no queremos duplicados o internos
            record.pop('policyholder_birth_date', None)  # Por privacidad, no incluimos fecha nacimiento
            
            data.append(record)
        
        df = pd.DataFrame(data)
        
        # Añadir algunas columnas derivadas que son comunes en datasets reales
        df['age_of_policyholder'] = df['policyholder_age']
        
        # CORRECCIÓN: Buscar la columna de edad del vehículo de manera dinámica
        vehicle_age_columns = [col for col in df.columns if 'vehicle_age' in col]
        if vehicle_age_columns:
            df['age_of_car'] = df[vehicle_age_columns[0]]
            logging.info(f"Usando columna {vehicle_age_columns[0]} para age_of_car")
        else:
            logging.warning("No se encontró columna de edad del vehículo")
            df['age_of_car'] = 0
        
        logging.info(f"Generación completada. Shape: {df.shape}")
        
        # Calcular tasa de fraude de manera segura
        fraud_counts = df['fraud_reported'].value_counts(normalize=True)
        fraud_rate = fraud_counts.get('Y', 0)
        logging.info(f"Tasa de fraude: {fraud_rate:.2%}")
        
        return df
    
    def save_dataset(self, df: pd.DataFrame):
        """
        Guarda el dataset generado en la ruta especificada.
        """
        output_path = Path(self.config['output']['path'])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False)
        logging.info(f"Dataset guardado en {output_path}")

def main():
    """
    Función principal para ejecutar la generación de datos.
    """
    # Verificar que existe el archivo de configuración
    config_path = Path("config/data_generation.yaml")
    if not config_path.exists():
        logging.error(f"No se encontró el archivo de configuración: {config_path}")
        logging.info("Creando directorio config/...")
        Path("config").mkdir(exist_ok=True)
        logging.info("Por favor, crea el archivo config/data_generation.yaml")
        return
    
    generator = InsuranceClaimsGenerator("config/data_generation.yaml")
    df = generator.generate_dataset()
    generator.save_dataset(df)
    
    # Mostrar estadísticas básicas
    print("\n" + "="*50)
    print("RESUMEN DEL DATASET GENERADO")
    print("="*50)
    print(f"Total de registros: {len(df):,}")
    print(f"Columnas: {df.shape[1]}")
    
    fraud_counts = df['fraud_reported'].value_counts()
    fraud_rate = fraud_counts.get('Y', 0) / len(df) if len(df) > 0 else 0
    print(f"Reclamaciones fraudulentas: {fraud_counts.get('Y', 0)} ({fraud_rate:.1%})")
    
    print(f"Monto total reclamado: ${df['total_claim_amount'].sum():,.0f}")
    print(f"Monto promedio por reclamación: ${df['total_claim_amount'].mean():,.0f}")
    print(f"Edad promedio del asegurado: {df['policyholder_age'].mean():.1f} años")
    
    # Buscar la columna de edad del vehículo
    vehicle_age_cols = [col for col in df.columns if 'vehicle_age' in col]
    if vehicle_age_cols:
        print(f"Edad promedio del vehículo: {df[vehicle_age_cols[0]].mean():.1f} años")
    
    print("\nDistribución por severidad:")
    print(df['incident_severity'].value_counts())
    print("="*50)

if __name__ == "__main__":
    main()