"""empty message

Revision ID: 85c9079c644b
Revises: cab1b4a0e9f2
Create Date: 2021-06-24 11:02:03.747798

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '85c9079c644b'
down_revision = 'cab1b4a0e9f2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tbl_student_course_request', sa.Column('accepted', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tbl_student_course_request', 'accepted')
    # ### end Alembic commands ###
