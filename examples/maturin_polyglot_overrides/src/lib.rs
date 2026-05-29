// Copyright 2026 Mark Kurtz
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

use pyo3::prelude::*;

/// A simple Rust greeting function exposed to Python.
#[pyfunction]
fn rust_greeting() -> PyResult<String> {
    Ok("Hello from the Rust side of the polyglot repo!".to_string())
}

/// The Python module defined in Rust using PyO3.
#[pymodule]
fn maturin_polyglot_overrides(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rust_greeting, m)?)?;
    Ok(())
}
