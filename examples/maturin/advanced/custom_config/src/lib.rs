use pyo3::prelude::*;

/// A simple Rust greeting function exposed to Python.
#[pyfunction]
fn rust_greeting() -> PyResult<String> {
    Ok("Hello from the Rust side of the polyglot repo!".to_string())
}

/// The Python module defined in Rust using PyO3.
#[pymodule]
fn maturin_custom_config(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rust_greeting, m)?)?;
    Ok(())
}
