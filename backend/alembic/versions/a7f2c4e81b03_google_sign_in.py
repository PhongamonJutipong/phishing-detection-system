"""รองรับเข้าสู่ระบบด้วยบัญชี Google

password_hash เป็น NULL ได้ (บัญชีที่สร้างจาก Google ไม่มีรหัสผ่าน)
และเพิ่ม google_linked_at บันทึกเวลาที่ยืนยันความเป็นเจ้าของอีเมลกับ Google

Revision ID: a7f2c4e81b03
Revises: c61a1bbdea89
Create Date: 2026-10-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7f2c4e81b03'
down_revision: Union[str, None] = 'c61a1bbdea89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table เพราะ SQLite เปลี่ยน nullable ของคอลัมน์ตรง ๆ ไม่ได้
    # ต้องสร้างตารางใหม่แล้วย้ายข้อมูล ซึ่ง Alembic จัดการให้ในโหมดนี้
    with op.batch_alter_table('app_user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_linked_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column('password_hash', existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    # บัญชีที่ไม่มีรหัสผ่านจะย้อนกลับไม่ได้เพราะคอลัมน์ต้องเป็น NOT NULL
    # ลบบัญชีที่เข้าสู่ระบบได้ทาง Google เท่านั้นออกก่อน ไม่งั้นการย้อนจะล้มกลางทาง
    op.execute(sa.text("DELETE FROM user_session WHERE user_id IN (SELECT user_id FROM app_user WHERE password_hash IS NULL)"))
    op.execute(sa.text("DELETE FROM app_user WHERE password_hash IS NULL"))
    with op.batch_alter_table('app_user', schema=None) as batch_op:
        batch_op.alter_column('password_hash', existing_type=sa.String(length=255), nullable=False)
        batch_op.drop_column('google_linked_at')
