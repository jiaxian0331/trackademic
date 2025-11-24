<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Log In</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>

<div class="container">
    <div class="side-image login-image"></div>
    <div class="form-box glass">
        <h2>Log In</h2>
        <form action="/login" method="POST">
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button class="button" type="submit">Log In</button>
        </form>
        <p>Don't have an account? <a href="/signup">Sign Up</a></p>
    </div>
</div>

</body>
</html>
