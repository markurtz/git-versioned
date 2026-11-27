//! The beam API.

/// Parse a beam definition.
pub fn parse(text: &str) -> usize {
    text.len()
}

/// Render a beam definition.
pub fn render(size: usize) -> String {
    "=".repeat(size)
}
