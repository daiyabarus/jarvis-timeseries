# dbengine.py
import toml
from gentable import Base  # , ServiceBase
from omegaconf import DictConfig
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateSchema
from sqlalchemy_utils import create_database, database_exists


def create_db(cfg: DictConfig) -> None:
    try:
        engine = create_engine(
            f"{cfg.dialect}://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.database}"
        )
        if not database_exists(engine.url):
            create_database(engine.url)

        conn = engine.connect()

        # Creates schemas if not exists
        for schema in ["general", "service"]:
            conn.execute(CreateSchema(schema, if_not_exists=True))
            conn.commit()

        # Create tables for both bases
        Base.metadata.create_all(engine)
        # ServiceBase.metadata.create_all(engine)

        conn.close()
    except KeyError as e:
        print(f"Configuration key missing: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    try:
        with open(".streamlit/secrets.toml") as f:
            cfg = DictConfig(toml.loads(f.read()))
        create_db(cfg.connections.postgresql)
    except KeyError as e:
        print(f"Configuration key missing at top level: {e}")
    except Exception as e:
        print(f"An error occurred while loading the configuration: {e}")
