from sqlalchemy import create_engine, text
engine = create_engine("postgresql+psycopg://sports_user:TuPassFuerte123@127.0.0.1:5432/sports_booking")
with engine.connect() as conn:
    print(conn.execute(text("select current_database(), version()")).first())
