"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}


# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}


def upgrade():
    """ Upgrade """
    ${upgrades if upgrades else "pass"}


def downgrade():
    """ Downgrade """
    ${downgrades if downgrades else "pass"}
