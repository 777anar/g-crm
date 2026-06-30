class CRMDomainError(Exception):
    pass


class CustomerAlreadyArchivedError(CRMDomainError):
    pass


class LeadAlreadyConvertedError(CRMDomainError):
    pass


class InvalidLeadSourceChannelError(CRMDomainError):
    pass
