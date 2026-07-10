from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class Plant(Base):
    __tablename__ = 'plants'
    
    plant_id = Column(String(50), primary_key=True)
    plant_name = Column(String(100), nullable=False)
    capacity_kw = Column(Float, nullable=False)
    location = Column(String(100), nullable=True)
    
    equipments = relationship('Equipment', back_populates='plant', cascade='all, delete-orphan')
    generation_records = relationship('GenerationData', back_populates='plant', cascade='all, delete-orphan')
    weather_records = relationship('WeatherData', back_populates='plant', cascade='all, delete-orphan')
    anomalies = relationship('Anomaly', back_populates='plant', cascade='all, delete-orphan')
    model_results = relationship('ModelResult', back_populates='plant', cascade='all, delete-orphan')
    healths = relationship('InverterHealth', back_populates='plant', cascade='all, delete-orphan')

class Equipment(Base):
    __tablename__ = 'equipment'
    
    equipment_id = Column(String(50), primary_key=True)
    plant_id = Column(String(50), ForeignKey('plants.plant_id'), nullable=False)
    equipment_type = Column(String(50), nullable=False) # e.g. 'Inverter'
    status = Column(String(50), default='Active')
    
    plant = relationship('Plant', back_populates='equipments')

class GenerationData(Base):
    __tablename__ = 'generation_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    plant_id = Column(String(50), ForeignKey('plants.plant_id'), nullable=False)
    source_key = Column(String(50), nullable=False, index=True) # Inverter ID
    dc_power = Column(Float, nullable=False)
    ac_power = Column(Float, nullable=False)
    daily_yield = Column(Float, nullable=False)
    total_yield = Column(Float, nullable=False)
    
    plant = relationship('Plant', back_populates='generation_records')

class WeatherData(Base):
    __tablename__ = 'weather_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    plant_id = Column(String(50), ForeignKey('plants.plant_id'), nullable=False)
    ambient_temperature = Column(Float, nullable=False)
    module_temperature = Column(Float, nullable=False)
    irradiation = Column(Float, nullable=False)
    rainfall = Column(Float, nullable=False)
    hours_since_last_rain = Column(Float, nullable=False)
    
    plant = relationship('Plant', back_populates='weather_records')

class Anomaly(Base):
    __tablename__ = 'anomalies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    plant_id = Column(String(50), ForeignKey('plants.plant_id'), nullable=False)
    equipment_id = Column(String(50), nullable=False, index=True) # Inverter ID
    issue = Column(String(200), nullable=False)
    severity = Column(String(50), nullable=False) # 'LOW', 'MEDIUM', 'HIGH'
    probable_cause = Column(String(500), nullable=True)
    recommended_action = Column(String(500), nullable=True)
    financial_loss_rs = Column(Float, default=0.0)
    
    plant = relationship('Plant', back_populates='anomalies')

class InverterHealth(Base):
    __tablename__ = 'inverter_health'
    
    source_key = Column(String(50), primary_key=True)
    plant_id = Column(String(50), ForeignKey('plants.plant_id'), nullable=False)
    health_score = Column(Float, nullable=False)
    risk_level = Column(String(50), nullable=False) # 'LOW', 'MEDIUM', 'HIGH'
    status = Column(String(50), nullable=False) # 'Healthy', 'Warning', 'Critical'
    average_efficiency = Column(Float, nullable=False)
    total_runtime_hours = Column(Float, nullable=False)
    anomaly_count = Column(Integer, default=0)
    recommended_action = Column(String(500), nullable=True)
    
    plant = relationship('Plant', back_populates='healths')

class ModelResult(Base):
    __tablename__ = 'model_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(String(50), ForeignKey('plants.plant_id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    predicted_generation = Column(Float, nullable=False)
    actual_generation = Column(Float, nullable=False)
    error_percentage = Column(Float, nullable=False)
    model_version = Column(String(100), nullable=False)
    
    plant = relationship('Plant', back_populates='model_results')
