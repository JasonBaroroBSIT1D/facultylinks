import click
from flask import current_app

from app.extensions import db
from app.models import User, UserRole
from app.services.passwords import hash_password


def register_cli(app):
    @app.cli.command("create-admin")
    @click.argument("email")
    @click.argument("password")
    @click.option("--name", default="System Administrator", help="Display name")
    def create_admin(email: str, password: str, name: str):
        """Create or reset an administrator account (no demo seeding)."""
        email = email.strip().lower()
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")
        user = User.query.filter_by(email=email).first()
        if user:
            user.password_hash = hash_password(password)
            user.role = UserRole.admin
            user.full_name = name
            user.is_active = True
            click.echo(f"Updated admin: {email}")
        else:
            user = User(
                email=email,
                password_hash=hash_password(password),
                role=UserRole.admin,
                full_name=name,
                is_active=True,
            )
            db.session.add(user)
            click.echo(f"Created admin: {email}")
        db.session.commit()

    @app.cli.command("correct-admin-account")
    @click.argument("current_email")
    def correct_admin_account(current_email: str):
        """Fix an admin account email/password (prompts; does not echo password)."""
        current_email = current_email.strip().lower()
        user = User.query.filter_by(email=current_email).first()
        if not user:
            raise click.ClickException(f"No account found for: {current_email}")
        if user.role != UserRole.admin:
            raise click.ClickException("That account is not an administrator — refusing to change role.")

        new_email = click.prompt("New admin email", type=str).strip().lower()
        if not new_email or "@" not in new_email:
            raise click.ClickException("Enter a valid email address.")
        if new_email != current_email and User.query.filter_by(email=new_email).first():
            raise click.ClickException("That email is already in use by another account.")

        password = click.prompt(
            "New password",
            hide_input=True,
            confirmation_prompt=True,
        )
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")

        user.email = new_email
        user.password_hash = hash_password(password)
        user.role = UserRole.admin
        user.is_active = True
        db.session.commit()
        click.echo("Administrator account updated.")

    @app.cli.command("create-user")
    @click.argument("role", type=click.Choice(["admin", "reviewer", "faculty"], case_sensitive=False))
    @click.argument("email")
    @click.argument("password")
    @click.option("--name", default=None)
    def create_user(role: str, email: str, password: str, name: str | None):
        """Create a test user (admin, reviewer, or faculty)."""
        email = email.strip().lower()
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")
        role_enum = UserRole(role.lower())
        display = name or email.split("@")[0].replace(".", " ").title()
        if User.query.filter_by(email=email).first():
            raise click.ClickException("Email already exists.")
        db.session.add(
            User(
                email=email,
                password_hash=hash_password(password),
                role=role_enum,
                full_name=display,
                is_active=True,
            )
        )
        db.session.commit()
        click.echo(f"Created {role_enum.value}: {email}")

    @app.cli.command("assign-reviewer")
    @click.argument("reviewer_email")
    @click.argument("faculty_email")
    def assign_reviewer(reviewer_email: str, faculty_email: str):
        """Link a reviewer to a faculty member for document access."""
        from app.models import ReviewerAssignment

        rev = User.query.filter_by(email=reviewer_email.strip().lower(), role=UserRole.reviewer).first()
        fac = User.query.filter_by(email=faculty_email.strip().lower(), role=UserRole.faculty).first()
        if not rev or not fac:
            raise click.ClickException("Reviewer and faculty accounts must exist with correct roles.")
        exists = ReviewerAssignment.query.filter_by(
            reviewer_user_id=rev.id,
            faculty_user_id=fac.id,
        ).first()
        if exists:
            click.echo("Assignment already exists.")
            return
        db.session.add(ReviewerAssignment(reviewer_user_id=rev.id, faculty_user_id=fac.id))
        db.session.commit()
        click.echo(f"Assigned {rev.email} → {fac.email}")
