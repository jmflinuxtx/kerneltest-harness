#!/usr/bin/env python

from sqlalchemy.exc import SQLAlchemyError
from alembic.config import Config
from alembic import command

from kerneltest import db, default_config


try:
    engine = db.initialize(default_config.config.load_config())
    db.Base.metadata.create_all(engine)
    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")

    session = db.Session()
    session.add(db.Release(releasenum="30", support="RELEASE"))
    session.commit()
    db.Session.remove()
except SQLAlchemyError as err:
    print(err)
