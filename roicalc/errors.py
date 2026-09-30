"""Named errors suitable for CLI presentation."""

class ROIError(Exception):
    pass

class ValidationError(ROIError):
    pass

class DuplicateBaselineError(ROIError):
    pass

class BaselineMissingError(ROIError):
    pass

class StoreCorruptError(ROIError):
    pass

class StoreIOError(ROIError):
    pass
