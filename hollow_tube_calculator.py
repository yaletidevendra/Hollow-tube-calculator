import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Hollow Tube Calculator", page_icon="📐", layout="wide")

st.title("Hollow Tube Structural Calculator")
st.caption("First web version of the Excel calculation for circular hollow aluminium tubes.")

with st.sidebar:
    st.header("Geometry")
    dmin = st.number_input("Minimum external diameter (mm)", min_value=0.1, value=28.0, step=1.0)
    dmax = st.number_input("Maximum external diameter (mm)", min_value=0.1, value=45.0, step=1.0)
    dstep = st.number_input("Diameter increment (mm)", min_value=0.1, value=1.0, step=0.5)
    tmin = st.number_input("Minimum wall thickness (mm)", min_value=0.1, value=1.0, step=0.5)
    tmax = st.number_input("Maximum wall thickness (mm)", min_value=0.1, value=2.0, step=0.5)
    tstep = st.number_input("Thickness increment (mm)", min_value=0.1, value=1.0, step=0.5)

    st.header("Material")
    rho = st.number_input("Aluminium density (kg/m³)", min_value=1.0, value=2700.0, step=50.0)
    young = st.number_input("Young's modulus (MPa)", min_value=1.0, value=69000.0, step=1000.0)
    yield_strength = st.number_input("Yield strength (MPa)", min_value=1.0, value=240.0, step=10.0)

    st.header("Loading and supports")
    length = st.number_input("Unsupported tube length (mm)", min_value=1.0, value=3175.0, step=100.0)
    column_end = st.selectbox(
        "Column end condition",
        ["Pinned-Pinned", "Fixed-Fixed", "Fixed-Pinned", "Fixed-Free"],
        index=1,
    )
    applied_load = st.number_input(
        "Applied compressive load (N)", min_value=0.0, value=98.10, step=10.0,
        help="Enter a positive value for compression.",
    )
    distributed_load = st.number_input("Uniformly distributed load (N/mm)", min_value=0.0, value=0.077244094, format="%.9f")
    beam_support = st.selectbox(
        "Beam support condition",
        ["Fixed-Fixed", "Simply Supported", "Cantilever"],
        index=0,
    )
    deflection_limit = st.number_input("Maximum allowable deflection (mm)", min_value=0.0, value=10.0, step=1.0)

st.subheader("Calculation settings")
st.write("The app generates every diameter/thickness combination in the selected ranges, excluding geometries where the inner diameter is zero or negative.")

k_factors = {
    "Pinned-Pinned": 1.0,
    "Fixed-Fixed": 0.5,
    "Fixed-Pinned": 0.7,
    "Fixed-Free": 2.0,
}
k = k_factors[column_end]

beam_coefficients = {
    "Fixed-Fixed": ("wL²/12", 12.0, "wL⁴/(384EI)", 384.0),
    "Simply Supported": ("wL²/8", 8.0, "5wL⁴/(384EI)", 384.0 / 5.0),
    "Cantilever": ("wL²/2", 2.0, "wL⁴/(8EI)", 8.0),
}
moment_formula, moment_divisor, deflection_formula, deflection_divisor = beam_coefficients[beam_support]

if dmax < dmin:
    st.error("Maximum external diameter must be greater than or equal to minimum external diameter.")
elif tmax < tmin:
    st.error("Maximum wall thickness must be greater than or equal to minimum wall thickness.")
else:
    # Match Excel's INT((max-min)/step)+1 range generation.
    n_d = int((dmax - dmin) / dstep) + 1
    n_t = int((tmax - tmin) / tstep) + 1
    if n_d * n_t > 100_000:
        st.error("This input range creates more than 100,000 combinations. Increase the increments.")
    else:
        rows = []
        row_number = 0
        for i in range(n_d):
            diameter = dmin + i * dstep
            for j in range(n_t):
                thickness = tmin + j * tstep
                if diameter <= 2 * thickness:
                    continue

                row_number += 1
                inner_d = diameter - 2 * thickness
                area_mm2 = math.pi / 4.0 * (diameter**2 - inner_d**2)
                inertia_mm4 = math.pi / 64.0 * (diameter**4 - inner_d**4)
                section_modulus_mm3 = inertia_mm4 / (diameter / 2.0)

                area_cm2 = area_mm2 / 100.0
                inertia_cm4 = inertia_mm4 / 10_000.0
                section_modulus_cm3 = section_modulus_mm3 / 1000.0
                mass_per_m = area_mm2 * rho / 1_000_000.0
                radius_gyration = math.sqrt(inertia_mm4 / area_mm2)
                slenderness = k * length / radius_gyration

                effective_length = k * length
                euler_load = math.pi**2 * young * inertia_mm4 / effective_length**2
                euler_stress = euler_load / area_mm2
                yield_load = area_mm2 * yield_strength
                column_stress = applied_load / area_mm2

                max_moment = distributed_load * length**2 / moment_divisor
                beam_stress = max_moment / section_modulus_mm3
                beam_deflection = (
                    distributed_load * length**4
                    / (deflection_divisor * young * inertia_mm4)
                )

                if beam_stress > yield_strength:
                    beam_result = "FAIL - YIELD"
                elif beam_deflection > deflection_limit:
                    beam_result = "FAIL - DEFLECTION"
                else:
                    beam_result = "PASS"

                if applied_load <= 0:
                    column_result = "NO COMPRESSION"
                elif applied_load >= yield_load:
                    column_result = "FAIL - YIELD"
                elif applied_load >= euler_load:
                    column_result = "FAIL - BUCKLING"
                elif euler_stress >= yield_strength:
                    column_result = "CHECK INELASTIC BUCKLING"
                else:
                    column_result = "PASS"

                final_result = "YES" if beam_result == "PASS" and column_result == "PASS" else "NO"

                rows.append({
                    "No.": row_number,
                    "Profile": f"Tube {diameter:.1f}x{thickness:.1f}",
                    "External diameter (mm)": diameter,
                    "Wall thickness (mm)": thickness,
                    "Inner diameter (mm)": inner_d,
                    "Area (cm²)": area_cm2,
                    "Second moment I (cm⁴)": inertia_cm4,
                    "Section modulus W (cm³)": section_modulus_cm3,
                    "Polar moment 2I (cm⁴)": 2.0 * inertia_cm4,
                    "Polar modulus 2W (cm³)": 2.0 * section_modulus_cm3,
                    "Mass (kg/m)": mass_per_m,
                    "Slenderness KL/r": slenderness,
                    "Beam stress (MPa)": beam_stress,
                    "Beam deflection (mm)": beam_deflection,
                    "Beam result": beam_result,
                    "Column stress (MPa)": column_stress,
                    "Euler buckling load (N)": euler_load,
                    "Column result": column_result,
                    "Final result": final_result,
                })

        df = pd.DataFrame(rows)
        if df.empty:
            st.warning("No valid tube geometries were generated. Check the diameter and thickness ranges.")
        else:
            total = len(df)
            passed = int((df["Final result"] == "YES").sum())
            c1, c2, c3 = st.columns(3)
            c1.metric("Valid profiles", total)
            c2.metric("Profiles passing both checks", passed)
            c3.metric("Profiles not passing both checks", total - passed)

            st.subheader("Results")
            st.dataframe(df, use_container_width=True, hide_index=True)

            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            excel_buffer = None
            try:
                import io
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Tube results")
                excel_buffer.seek(0)
            except Exception:
                pass

            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button(
                    "Download results as CSV",
                    data=csv_data,
                    file_name="hollow_tube_results.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with col_b:
                if excel_buffer is not None:
                    st.download_button(
                        "Download results as Excel",
                        data=excel_buffer,
                        file_name="hollow_tube_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

st.divider()
st.caption(
    "Engineering note: this first version reproduces the equations supplied in the Excel LET formula. "
    "It is a calculation aid, not a certified design check. Confirm assumptions, load cases, safety factors, "
    "local buckling, imperfections, code requirements and units with a qualified engineer before relying on results."
)
