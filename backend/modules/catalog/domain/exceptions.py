class CatalogDomainError(Exception):
    pass


class InvalidSlabTransitionError(CatalogDomainError):
    pass


class DuplicateSlabNumberError(CatalogDomainError):
    pass
