"""Add day_off new columns

Revision ID: 9b85c14fa8a7
Revises: 16328eae4b5f
Create Date: 2024-02-23 14:48:48.461237

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm.session import Session
from zou.migrations.utils.base import BaseMixin
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import UUIDType


# revision identifiers, used by Alembic.
revision = "9b85c14fa8a7"
down_revision = "16328eae4b5f"
branch_labels = None
depends_on = None

base = declarative_base()


class DayOff(base, BaseMixin):
    """
    Tells that someone will have a day off this day.
    """

    __tablename__ = "day_off"
    date = sa.Column(sa.Date, nullable=False)
    end_date = sa.Column(sa.Date, nullable=True)
    description = sa.Column(sa.Text)
    person_id = sa.Column(
        UUIDType(binary=False), sa.ForeignKey("person.id"), index=True
    )
    __table_args__ = (
        sa.UniqueConstraint("person_id", "date", name="day_off_uc"),
        sa.CheckConstraint("date <= end_date", name="day_off_date_check"),
    )


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("day_off", schema=None) as batch_op:
        batch_op.add_column(sa.Column("end_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.create_check_constraint(
            "day_off_date_check", "date <= end_date"
        )
    session = Session(bind=op.get_bind())
    session.query(DayOff).update({DayOff.end_date: DayOff.date})
    session.commit()
    with op.batch_alter_table("day_off", schema=None) as batch_op:
        batch_op.alter_column("end_date", nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("day_off", schema=None) as batch_op:
        batch_op.drop_constraint("day_off_date_check", type_="check")
        batch_op.drop_column("description")
        batch_op.drop_column("end_date")

    # ### end Alembic commands ###
