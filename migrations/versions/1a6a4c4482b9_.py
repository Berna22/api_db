"""empty message

Revision ID: 1a6a4c4482b9
Revises: 9539f2a3e4a4
Create Date: 2021-06-22 10:09:52.358840

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a6a4c4482b9'
down_revision = '9539f2a3e4a4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tbl_course', sa.Column('deleted', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    op.add_column('tbl_student_course', sa.Column('deleted', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    op.add_column('tbl_user', sa.Column('deleted', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    op.add_column('tbl_user_session', sa.Column('deleted', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tbl_user_session', 'deleted')
    op.drop_column('tbl_user', 'deleted')
    op.drop_column('tbl_student_course', 'deleted')
    op.drop_column('tbl_course', 'deleted')
    # ### end Alembic commands ###