/* ===========================
   SIGNUP
=========================== */
async function signup(event) {
    event.preventDefault();
    const name     = document.getElementById("name").value;
    const email    = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const response = await fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ name, email, password })
        });
        const data = await response.json();
        if (response.ok) {
            alert(data.message);
            window.location.href = "/";
        } else {
            alert(data.message);
        }
    } catch (error) {
        console.error(error);
        alert("Something went wrong. Please try again.");
    }
}

/* ===========================
   LOGIN
=========================== */
document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", async function (event) {
            event.preventDefault();
            const email    = document.getElementById("loginEmail").value;
            const password = document.getElementById("loginPassword").value;

            try {
                const response = await fetch("/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "include",
                    body: JSON.stringify({ email, password })
                });
                const data = await response.json();
                if (response.ok) {
                    window.location.href = "/dashboard";
                } else {
                    alert(data.message);
                }
            } catch (error) {
                console.error(error);
                alert("Login failed. Please try again.");
            }
        });
    }
});
