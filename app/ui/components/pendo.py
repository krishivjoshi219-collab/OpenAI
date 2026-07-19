"""Pendo analytics snippet injection for Streamlit."""

from __future__ import annotations

import base64

import streamlit as st


def inject_pendo() -> None:
    """Inject the Pendo install snippet into the parent frame via ``st.iframe``.

    Streamlit strips ``<script>`` tags from ``st.markdown``, so the snippet is
    loaded via an iframe with a base64-encoded ``data:text/html`` source.
    The script targets ``window.parent`` so that Pendo runs on the main page.
    A guard flag prevents duplicate injection on Streamlit re-renders.
    """

    html = """<script>
(function(){
    var pw=window.parent;
    if(pw.__pendo_injected)return;
    pw.__pendo_injected=true;
    (function(apiKey){
        (function(p,e,n,d,o){var v,w,x,y,z;o=p[d]=p[d]||{};o._q=o._q||[];
        v=['initialize','identify','updateOptions','pageLoad','track','trackAgent'];for(w=0,x=v.length;w<x;++w)(function(m){
        o[m]=o[m]||function(){o._q[m===v[0]?'unshift':'push']([m].concat([].slice.call(arguments,0)));};})(v[w]);
        y=e.createElement(n);y.async=!0;y.src='https://cdn.pendo.io/agent/static/'+apiKey+'/pendo.js';
        z=e.getElementsByTagName(n)[0];z.parentNode.insertBefore(y,z);})(pw,pw.document,'script','pendo');
    })('eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhY2VudGVyIjoidXMiLCJrZXkiOiI3OTJkODgwOWFhNzViMTU2OGI4MzdmYzIwN2RjMDRlOThhYjRiMzljM2ZiOTZjZTEyZmUxZTY2YWMwNjZhYzJlNWM4Y2NlOWUxODQ5MmRlYzY3ODMwNzAzMTQzNmIxZDY5MGVkYzg5NGQzYmVmOTgzZTlkOTI3ZTZkZmY2MTEyOTNhMTc0ODc3YTk3ZmYyM2JhMDI3NGM4MDFkMjk1M2U3YTllNjUzOTBjM2U1NTUwNzkxZTg1NWQzMjlkMjU5MDMuMTE1NTgxNWJiNTRhMjBhNDZlMjk0OGJmZDg0MTkwNmMuNDhlMTM0OGE2ZTQ5MDgyNzZlOTAyYTRkM2Q1YTA4YzYwNjQxZTUzYjg1YmU2ZDgzZmJiZDAyNjczMjlkNGJlOSJ9.VTAJlLem34kAxkET12f65dj0ztWQEvJql7AL4_BV1L7URK2MEzQdkBjXqjg0R_KYefAlAKjva84b9tn6zlOPEnIdIClxg_RyBx232gqSxUXOzsPlh7PGZ__lYXkhPlqqY0cG1cQxXEuQ8ShwizuNWB0L80osrTdHi8MpaffAlpw');
    pw.pendo.initialize({visitor:{id:''}});
})();
</script>"""

    b64 = base64.b64encode(html.encode("utf-8")).decode("utf-8")
    st.iframe(src=f"data:text/html;base64,{b64}", height=0)

