"""
Migration script to update role names and permissions.
Run this script to migrate from old role structure (SUPERADMIN/ADMIN/COACH) 
to new structure (ADMIN/USER/COACH).
"""
import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "bafl_database.db"


def migrate_database():
    """Migrate database to new role structure."""
    print("Starting database migration...")
    
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("No migration needed - fresh database will be created with new structure")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Step 1: Update user roles
        print("\n1. Updating user roles...")
        
        # First, check what roles and users exist
        cursor.execute("SELECT id, username, role FROM users ORDER BY id")
        all_users = cursor.fetchall()
        print(f"   Found users:")
        for uid, uname, urole in all_users:
            print(f"      ID {uid}: {uname} ({urole})")
        
        # Convert SUPERADMIN -> ADMIN (keep uppercase for SQLAlchemy enum)
        cursor.execute("""
            UPDATE users 
            SET role = 'ADMIN' 
            WHERE role = 'SUPERADMIN'
        """)
        superadmin_count = cursor.rowcount
        print(f"\n   - Converted {superadmin_count} SUPERADMIN(s) to ADMIN")
        
        # Convert old ADMIN users (not the converted superadmin) -> USER
        # Get the ID of the first user (original superadmin, now admin)
        cursor.execute("SELECT MIN(id) FROM users")
        first_user_id = cursor.fetchone()[0]
        
        cursor.execute("""
            UPDATE users 
            SET role = 'USER' 
            WHERE role = 'ADMIN'
            AND id != ?
        """, (first_user_id,))
        admin_count = cursor.rowcount
        print(f"   - Converted {admin_count} old ADMIN(s) to USER")
        
        # COACH stays COACH
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'COACH'")
        coach_count = cursor.fetchone()[0]
        print(f"   - {coach_count} COACH(es) remain unchanged")
        
        # Step 2: Update role_permissions table
        print("\n2. Updating role permissions...")
        
        # SUPERADMIN -> ADMIN in role_permissions (keep uppercase)
        cursor.execute("""
            UPDATE role_permissions 
            SET role = 'ADMIN' 
            WHERE role = 'SUPERADMIN'
        """)
        print(f"   - Updated {cursor.rowcount} SUPERADMIN permission mappings to ADMIN")
        
        # ADMIN -> USER in role_permissions (keep uppercase)
        cursor.execute("""
            UPDATE role_permissions 
            SET role = 'USER' 
            WHERE role = 'ADMIN'
        """)
        print(f"   - Updated {cursor.rowcount} old ADMIN permission mappings to USER")
        
        # Step 3: Clear old permissions and prepare for new ones
        print("\n3. Clearing old permission mappings...")
        cursor.execute("DELETE FROM role_permissions")
        print(f"   - Cleared all role permission mappings (will be recreated on restart)")
        
        # Step 4: Update/delete old permissions
        print("\n4. Updating permission types...")
        
        # Delete old permission types that no longer exist
        old_permissions = [
            'CREATE_SUPERADMIN',
            'CREATE_ADMIN'
        ]
        
        for perm in old_permissions:
            cursor.execute("DELETE FROM permissions WHERE name = ?", (perm,))
            if cursor.rowcount > 0:
                print(f"   - Deleted old permission: {perm}")
        
        # Rename permissions
        permission_renames = {
            'VIEW_USERS': 'VIEW_ALL_USERS',
            'EDIT_USER': 'EDIT_ALL_USERS'
        }
        
        for old_name, new_name in permission_renames.items():
            cursor.execute("""
                UPDATE permissions 
                SET name = ?, description = ? 
                WHERE name = ?
            """, (new_name, f"Permission: {new_name}", old_name))
            if cursor.rowcount > 0:
                print(f"   - Renamed permission: {old_name} -> {new_name}")
        
        # Step 5: Delete custom user permissions that reference old permissions
        print("\n5. Cleaning up user-specific permissions...")
        cursor.execute("DELETE FROM user_permissions WHERE permission_id NOT IN (SELECT id FROM permissions)")
        print(f"   - Removed {cursor.rowcount} orphaned user permission assignments")
        
        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("\n⚠️  IMPORTANT: Restart the server to recreate role permission mappings with new structure")
        
        # Display summary
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        
        cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        print("\nCurrent user role distribution:")
        for role, count in cursor.fetchall():
            print(f"   - {role.upper()}: {count} user(s)")
        
        cursor.execute("SELECT COUNT(*) FROM permissions")
        perm_count = cursor.fetchone()[0]
        print(f"\nTotal permissions: {perm_count}")
        
        print("\n" + "="*60)
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        raise
    
    finally:
        conn.close()


def show_current_state():
    """Show current database state without making changes."""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("\n" + "="*60)
        print("CURRENT DATABASE STATE")
        print("="*60)
        
        # Show users
        cursor.execute("SELECT id, name, username, role FROM users")
        print("\nUSERS:")
        for user_id, name, username, role in cursor.fetchall():
            print(f"   ID: {user_id} | {name} ({username}) | Role: {role.upper()}")
        
        # Show permissions
        cursor.execute("SELECT name FROM permissions ORDER BY name")
        print("\nPERMISSIONS:")
        for (perm,) in cursor.fetchall():
            print(f"   - {perm}")
        
        # Show role permissions
        cursor.execute("""
            SELECT DISTINCT role 
            FROM role_permissions 
            ORDER BY role
        """)
        print("\nROLE PERMISSION MAPPINGS:")
        for (role,) in cursor.fetchall():
            cursor.execute("""
                SELECT p.name 
                FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                WHERE rp.role = ?
                ORDER BY p.name
            """, (role,))
            perms = [p[0] for p in cursor.fetchall()]
            print(f"   {role.upper()}: {len(perms)} permission(s)")
            for perm in perms:
                print(f"      - {perm}")
        
        print("\n" + "="*60)
        
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        show_current_state()
    else:
        print("="*60)
        print("DATABASE MIGRATION TOOL")
        print("="*60)
        print("\nThis will migrate your database from:")
        print("  SUPERADMIN → ADMIN")
        print("  ADMIN → USER")
        print("  COACH → COACH (unchanged)")
        print("\nAnd update all permissions accordingly.")
        print("\nTo view current state without changes, run:")
        print("  python src/utils/migrate_roles.py --show")
        print("\n" + "="*60)
        
        response = input("\nProceed with migration? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            migrate_database()
        else:
            print("Migration cancelled.")
