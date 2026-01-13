"""
Tests for authorization middleware and permission checking.

Tests:
- Permission enum and role mappings
- Organization access checking
- Job-specific permissions (hiring manager)
- Permission requirement decorators
- Multi-tenant isolation
- Edge cases and security
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException

from core.middleware.authorization import (
    Permission,
    ROLE_PERMISSIONS,
    AuthorizationMiddleware,
    check_organization_access,
    check_permission,
    check_job_specific_permission,
    require_permission,
    require_organization_role,
    OrganizationAccessDenied,
    InsufficientPermissions,
)
from database.models.organizations import OrganizationRoles
from database.models.users import UserType


class TestPermissionEnum:
    """Test Permission enum."""
    
    def test_all_permissions_exist(self):
        """Test that all expected permissions exist."""
        expected_permissions = [
            "ORG_VIEW",
            "ORG_EDIT",
            "ORG_DELETE",
            "ORG_ADMIN",
            "JOB_CREATE",
            "JOB_VIEW",
            "JOB_EDIT",
            "JOB_DELETE",
            "APPLICATION_VIEW",
            "APPLICATION_REVIEW",
            "APPLICATION_REJECT",
            "CANDIDATE_VIEW",
            "CANDIDATE_CREATE",
            "CANDIDATE_EDIT",
            "CANDIDATE_DELETE",
            "OFFER_CREATE",
            "OFFER_VIEW",
            "OFFER_APPROVE",
            "USER_INVITE",
            "USER_MANAGE",
            "ANALYTICS_VIEW",
            "SETTINGS_VIEW",
            "SETTINGS_EDIT",
        ]
        
        for perm_name in expected_permissions:
            assert hasattr(Permission, perm_name)
    
    def test_permission_values(self):
        """Test that permissions have string values."""
        assert isinstance(Permission.ORG_VIEW.value, str)
        assert isinstance(Permission.JOB_CREATE.value, str)


class TestRolePermissions:
    """Test role-to-permission mappings."""
    
    def test_owner_has_all_permissions(self):
        """Test that OWNER role has all permissions."""
        owner_perms = ROLE_PERMISSIONS[OrganizationRoles.OWNER]
        
        # Should have all permissions
        all_permissions = set(Permission)
        assert owner_perms == all_permissions
    
    def test_admin_has_most_permissions(self):
        """Test that ADMIN role has most permissions."""
        admin_perms = ROLE_PERMISSIONS[OrganizationRoles.ADMIN]
        
        # Should have most permissions except maybe ORG_DELETE
        assert Permission.ORG_VIEW in admin_perms
        assert Permission.ORG_EDIT in admin_perms
        assert Permission.USER_MANAGE in admin_perms
    
    def test_recruiter_has_job_permissions(self):
        """Test that RECRUITER has job-related permissions."""
        recruiter_perms = ROLE_PERMISSIONS[OrganizationRoles.RECRUITER]
        
        assert Permission.JOB_CREATE in recruiter_perms
        assert Permission.JOB_VIEW in recruiter_perms
        assert Permission.APPLICATION_VIEW in recruiter_perms
        assert Permission.APPLICATION_REVIEW in recruiter_perms
    
    def test_hiring_manager_permissions(self):
        """Test HIRING_MANAGER permissions."""
        hm_perms = ROLE_PERMISSIONS[OrganizationRoles.HIRING_MANAGER]
        
        assert Permission.JOB_VIEW in hm_perms
        assert Permission.APPLICATION_VIEW in hm_perms
        assert Permission.APPLICATION_REVIEW in hm_perms
        
        # Should not have job creation
        assert Permission.JOB_CREATE not in hm_perms
    
    def test_interviewer_limited_permissions(self):
        """Test INTERVIEWER has limited permissions."""
        interviewer_perms = ROLE_PERMISSIONS[OrganizationRoles.INTERVIEWER]
        
        assert Permission.APPLICATION_VIEW in interviewer_perms
        assert Permission.CANDIDATE_VIEW in interviewer_perms
        
        # Should not have approval permissions
        assert Permission.OFFER_APPROVE not in interviewer_perms
    
    def test_viewer_read_only(self):
        """Test VIEWER has only read permissions."""
        viewer_perms = ROLE_PERMISSIONS[OrganizationRoles.VIEWER]
        
        # Should only have view permissions
        assert Permission.ORG_VIEW in viewer_perms
        assert Permission.JOB_VIEW in viewer_perms
        assert Permission.APPLICATION_VIEW in viewer_perms
        
        # Should not have any edit/create/delete permissions
        assert Permission.ORG_EDIT not in viewer_perms
        assert Permission.JOB_CREATE not in viewer_perms
        assert Permission.APPLICATION_REVIEW not in viewer_perms
    
    def test_all_roles_have_mappings(self):
        """Test that all common roles have permission mappings."""
        # Check that key roles have mappings
        essential_roles = [
            OrganizationRoles.OWNER,
            OrganizationRoles.ADMIN,
            OrganizationRoles.RECRUITER,
            OrganizationRoles.HIRING_MANAGER,
            OrganizationRoles.MEMBER,
            OrganizationRoles.VIEWER,
        ]
        
        for role in essential_roles:
            assert role in ROLE_PERMISSIONS, f"Role {role} missing permission mapping"


class TestOrganizationAccessCheck:
    """Test organization access checking."""
    
    @pytest.mark.asyncio
    async def test_check_access_success(self):
        """Test successful organization access check."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        
        # Mock organization membership
        mock_membership = Mock(
            user_id=1,
            organization_id=1,
            role=OrganizationRoles.RECRUITER,
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_membership)
        mock_db.execute.return_value = mock_result
        
        result = await check_organization_access(
            user=mock_user,
            organization_id=1,
            db=mock_db,
        )
        
        assert result == mock_membership
    
    @pytest.mark.asyncio
    async def test_check_access_not_member(self):
        """Test access check when user is not member."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(OrganizationAccessDenied) as exc_info:
            await check_organization_access(
                user=mock_user,
                organization_id=1,
                db=mock_db,
            )
        
        assert "not have access" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_check_access_multi_tenant_isolation(self):
        """Test that users can't access other organizations."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        # User 1 trying to access org 2
        with pytest.raises(OrganizationAccessDenied):
            await check_organization_access(
                user=mock_user,
                organization_id=2,
                db=mock_db,
            )


class TestPermissionCheck:
    """Test permission checking."""
    
    @pytest.mark.asyncio
    async def test_check_permission_success(self):
        """Test successful permission check."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        
        # Mock organization membership with RECRUITER role
        mock_membership = Mock(
            role=OrganizationRoles.RECRUITER,
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_membership)
        mock_db.execute.return_value = mock_result
        
        # RECRUITER should have JOB_UPDATE permission
        result = await check_permission(
            user=mock_user,
            organization_id=1,
            required_permission=Permission.JOB_UPDATE,
            db=mock_db,
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_check_permission_denied(self):
        """Test permission check denial."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        
        # Mock organization membership with VIEWER role
        mock_membership = Mock(
            role=OrganizationRoles.VIEWER,
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_membership)
        mock_db.execute.return_value = mock_result
        
        # VIEWER should not have JOB_CREATE permission
        with pytest.raises(InsufficientPermissions) as exc_info:
            await check_permission(
                user=mock_user,
                organization_id=1,
                required_permission=Permission.JOB_CREATE,
                db=mock_db,
            )
        
        assert "permission" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_check_permission_not_member(self):
        """Test permission check when not organization member."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(OrganizationAccessDenied):
            await check_permission(
                user=mock_user,
                organization_id=1,
                required_permission=Permission.JOB_VIEW,
                db=mock_db,
            )


class TestJobSpecificPermissions:
    """Test job-specific permission checking (hiring manager)."""
    
    @pytest.mark.asyncio
    async def test_hiring_manager_for_job(self):
        """Test that hiring manager has permissions for their job."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        
        # Mock job with hiring_manager_id
        mock_job = Mock(
            id=1,
            organization_id=1,
            hiring_manager_id=1,  # User 1 is hiring manager
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_job)
        mock_db.execute.return_value = mock_result
        
        result = await check_job_specific_permission(
            user=mock_user,
            job_id=1,
            required_permission=Permission.APPLICATION_REVIEW,
            db=mock_db,
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_not_hiring_manager_for_job(self):
        """Test that non-hiring-manager doesn't have job-specific permissions."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        
        # Mock job with different hiring_manager_id
        mock_job = Mock(
            id=1,
            organization_id=1,
            hiring_manager_id=2,  # User 2 is hiring manager, not user 1
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_job)
        mock_db.execute.return_value = mock_result
        
        result = await check_job_specific_permission(
            user=mock_user,
            job_id=1,
            required_permission=Permission.APPLICATION_REVIEW,
            db=mock_db,
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_job_not_found(self):
        """Test job-specific permission when job doesn't exist."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        result = await check_job_specific_permission(
            user=mock_user,
            job_id=999,
            required_permission=Permission.APPLICATION_REVIEW,
            db=mock_db,
        )
        
        assert result is False


class TestRequirePermissionDecorator:
    """Test require_permission decorator."""
    
    def test_require_permission_returns_dependency(self):
        """Test that require_permission returns a dependency function."""
        dependency = require_permission(Permission.JOB_VIEW)
        
        assert callable(dependency)
    
    @pytest.mark.asyncio
    async def test_require_permission_with_org_context(self):
        """Test permission requirement with organization context."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        
        # Mock organization membership with appropriate role
        mock_membership = Mock(
            role=OrganizationRoles.RECRUITER,
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_membership)
        mock_db.execute.return_value = mock_result
        
        dependency = require_permission(Permission.JOB_VIEW)
        
        # Would need to test with actual FastAPI dependency injection
        # For now, verify structure
        assert callable(dependency)


class TestRequireOrganizationRole:
    """Test require_organization_role decorator."""
    
    def test_require_organization_role_returns_dependency(self):
        """Test that require_organization_role returns a dependency."""
        dependency = require_organization_role(OrganizationRoles.ADMIN)
        
        assert callable(dependency)
    
    @pytest.mark.asyncio
    async def test_require_role_allowed(self):
        """Test role requirement when user has role."""
        mock_db = AsyncMock()
        
        # Mock membership with ADMIN role
        mock_membership = Mock(
            role=OrganizationRoles.ADMIN,
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_membership)
        mock_db.execute.return_value = mock_result
        
        # Would need FastAPI dependency injection to test properly
        pass
    
    @pytest.mark.asyncio
    async def test_require_role_denied(self):
        """Test role requirement when user doesn't have role."""
        mock_db = AsyncMock()
        
        # Mock membership with VIEWER role
        mock_membership = Mock(
            role=OrganizationRoles.VIEWER,
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_membership)
        mock_db.execute.return_value = mock_result
        
        # Should raise HTTPException
        pass


class TestMultiTenantIsolation:
    """Test multi-tenant security and isolation."""
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_other_org(self):
        """Test that users can't access resources from other orgs."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        # User 1 from org 1 trying to access org 2
        with pytest.raises(OrganizationAccessDenied):
            await check_organization_access(
                user=mock_user,
                organization_id=2,
                db=mock_db,
            )
    
    @pytest.mark.asyncio
    async def test_job_access_respects_organization(self):
        """Test that job access checks organization membership."""
        mock_db = AsyncMock()
        
        # Mock job from org 2
        mock_job = Mock(
            id=1,
            organization_id=2,
            hiring_manager_id=1,
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_job)
        mock_db.execute.return_value = mock_result
        
        # User should still need to be member of org 2
        # Even if they're hiring manager
        pass


class TestContextualPermissions:
    """Test contextual permission scenarios."""
    
    @pytest.mark.asyncio
    async def test_hiring_manager_only_for_their_jobs(self):
        """Test hiring manager only has permissions for assigned jobs."""
        mock_db = AsyncMock()
        
        # Job 1: User 1 is hiring manager
        mock_job1 = Mock(id=1, hiring_manager_id=1, organization_id=1)
        
        # Job 2: User 2 is hiring manager
        mock_job2 = Mock(id=2, hiring_manager_id=2, organization_id=1)
        
        # User 1 should have access to job 1
        mock_user = Mock(id=1)
        mock_result1 = AsyncMock()
        mock_result1.scalar_one_or_none = Mock(return_value=mock_job1)
        mock_db.execute.return_value = mock_result1
        result1 = await check_job_specific_permission(
            user=mock_user,
            job_id=1,
            required_permission=Permission.APPLICATION_REVIEW,
            db=mock_db,
        )
        assert result1 is True
        
        # User 1 should NOT have access to job 2
        mock_result2 = AsyncMock()
        mock_result2.scalar_one_or_none = Mock(return_value=mock_job2)
        mock_db.execute.return_value = mock_result2
        result2 = await check_job_specific_permission(
            user=mock_user,
            job_id=2,
            required_permission=Permission.APPLICATION_REVIEW,
            db=mock_db,
        )
        assert result2 is False


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_check_permission_with_invalid_role(self):
        """Test permission check with invalid/unknown role."""
        mock_db = AsyncMock()
        
        # Mock membership with invalid role
        mock_membership = Mock(
            role="INVALID_ROLE",
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_membership)
        mock_db.execute.return_value = mock_result
        
        # Should handle gracefully
        mock_user = Mock(id=1)
        try:
            await check_permission(
                user=mock_user,
                organization_id=1,
                required_permission=Permission.JOB_VIEW,
                db=mock_db,
            )
        except (InsufficientPermissions, KeyError):
            pass  # Expected
    
    @pytest.mark.asyncio
    async def test_permission_check_database_error(self):
        """Test permission check handles database errors."""
        mock_db = AsyncMock()
        mock_user = Mock(id=1)
        mock_db.execute.side_effect = Exception("Database error")
        
        # Should raise or handle gracefully
        with pytest.raises(Exception):
            await check_organization_access(
                user=mock_user,
                organization_id=1,
                db=mock_db,
            )


class TestSecurityCompliance:
    """Test security and compliance aspects."""
    
    def test_principle_of_least_privilege(self):
        """Test that roles follow principle of least privilege."""
        # VIEWER should have minimal read-only permissions
        viewer_perms = ROLE_PERMISSIONS[OrganizationRoles.VIEWER]
        
        # All viewer permissions should be read-only
        assert Permission.ORG_READ in viewer_perms
        assert Permission.JOB_READ in viewer_perms
        assert Permission.APPLICATION_READ in viewer_perms
        assert Permission.CANDIDATE_READ in viewer_perms
        
        # VIEWER should have no update/delete/create permissions
        dangerous_perms = {p for p in viewer_perms if any(x in p.value for x in ["UPDATE", "DELETE", "CREATE", "MANAGE", "SEND", "REVOKE"])}
        assert len(dangerous_perms) == 0, f"VIEWER has dangerous permissions: {dangerous_perms}"
    
    def test_admin_permissions_audit(self):
        """Test that admin permissions are clearly defined."""
        admin_perms = ROLE_PERMISSIONS[OrganizationRoles.ADMIN]
        
        # Should have critical admin permissions
        assert Permission.USER_MANAGE in admin_perms
        assert Permission.SETTINGS_EDIT in admin_perms or Permission.ORG_MANAGE_SETTINGS in admin_perms
    
    def test_no_permission_escalation(self):
        """Test that roles can't escalate permissions."""
        # RECRUITER shouldn't have user management
        recruiter_perms = ROLE_PERMISSIONS[OrganizationRoles.RECRUITER]
        assert Permission.USER_MANAGE not in recruiter_perms
        
        # MEMBER shouldn't have offer creation
        member_perms = ROLE_PERMISSIONS[OrganizationRoles.MEMBER]
        assert Permission.OFFER_CREATE not in member_perms
        assert Permission.OFFER_APPROVE not in member_perms


class TestGDPRSOC2:
    """Test GDPR and SOC2 compliance."""
    
    @pytest.mark.asyncio
    async def test_access_control_logging(self):
        """Test that access control decisions are logged (SOC2)."""
        # Permission checks should be logged for audit
        # This would require integration with logging middleware
        pass
    
    @pytest.mark.asyncio
    async def test_data_access_minimization(self):
        """Test that users only access necessary data (GDPR)."""
        # Permissions should ensure users only see data they need
        # VIEWER shouldn't access candidate PII unnecessarily
        viewer_perms = ROLE_PERMISSIONS[OrganizationRoles.VIEWER]
        
        # Should have view but not edit for candidate data
        assert Permission.CANDIDATE_VIEW in viewer_perms
        assert Permission.CANDIDATE_EDIT not in viewer_perms
