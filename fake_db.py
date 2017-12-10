from sqlalchemy import *
from database_setup import Base, Country, Team
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

session.query(Country).delete()
session.query(Team).delete()

sample_countries = [
    'Belarus', 'Croatia', 'Spain', 'Germany', 'Hungary', 'France', 'Poland', 
    'Sweden', 'Denmark', 'Turkey', 'Portugal', 'Macedonia', 'Norway', 'Romania', 
    'Austria', 'Iceland', 'Switzerland', 'Slovenia', 'Russia', 'Ukraine'
]

for country_name in sample_countries:
    country = Country(country_name)
    session.add(country)
session.commit()

sample_teams = {
    'HC Meshkov Brest': 1, 'RK Zagreb': 2, 'Aalborg Handbold': 9,
    'HBC Nantes': 6, 'Paris Saint-Germain': 6, 'SG Flensburg-Handewitt': 4,
    'THW Kiel': 4, 'Rhein-Neckar Lowen': 4, 'Pick Szeged': 5,
    'Veszprem KSE ': 5, 'RK Vardar': 12, 'Vive Kielce': 7,
    'Wisla Plock': 7, 'RK Celje': 18, 'Barcelona': 3, 'IFK Kristianstad': 8,
    'Skjern Handbold': 9, 'Montpellier Handball': 6,
    'RK Metalutg Skopje': 12, 'Elverum Handball': 13,
    'Dinamo Bucarest': 14, 'Chekhovskiye Medvedi': 19,
    'RK Gorenje Velenje': 18, 'CB Ademar Leon': 3,
    'Kadetten Schaffhausen': 17, 'Besiktas': 10,
    'HC Motor Zaporozhye': 20, 'Alpla Hard': 15, 'Riihimaki Cocks': 16,
    'Sporting CP ': 11
}

for team_name, team_country in sample_teams.iteritems():
    team = Team(team_name, "Sample description", team_country, 1)
    session.add(team)
session.commit()
