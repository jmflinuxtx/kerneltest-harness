"""Add the WARN status to test results

Revision ID: 02d7abf0710c
Revises: None
Create Date: 2017-05-04 10:51:49.144493
"""
from __future__ import print_function

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '02d7abf0710c'
down_revision = None


def upgrade():
    """ Upgrade the testresult enum """
    op.execute('COMMIT')  # See https://bitbucket.org/zzzeek/alembic/issue/123
    op.execute('ALTER TYPE testresult ADD VALUE \'WARN\'')


def downgrade():
    """ Downgrade """
    print("Operation not supported, we'll the enum as is")
