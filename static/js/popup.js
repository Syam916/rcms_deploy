// Function to show the pop-up
function showPopup(type, message) {
    const popup = document.getElementById('popup');
    const overlay = document.getElementById('overlay');
    const popupIcon = document.getElementById('popup-icon');
    const popupTitle = document.getElementById('popup-title');
    const popupMessage = document.getElementById('popup-message');
    const popupButton = document.getElementById('popup-button');

    // Reset classes for success, error, and warning
    popup.classList.remove('success', 'error', 'warning');

    // Customize the popup based on the type (success, error, warning)
    switch (type) {
        case 's': // Success
            popup.classList.add('success');
            popupIcon.innerHTML = '✔';  // Success checkmark icon
            popupTitle.textContent = 'SUCCESS';
            popupButton.style.backgroundColor = '#4CAF50'; // Green for success
            break;
        case 'e': // Error
            popup.classList.add('error');
            popupIcon.innerHTML = '❌';  // Error cross icon
            popupTitle.textContent = 'ERROR';
            popupButton.style.backgroundColor = '#f44336'; // Red for error
            break;
        case 'w': // Warning
            popup.classList.add('warning');
            popupIcon.innerHTML = '⚠';  // Warning icon
            popupTitle.textContent = 'WARNING';
            popupButton.style.backgroundColor = '#ff9800'; // Orange for warning
            break;
        default:
            console.warn("Unknown popup type"); // Handle unknown types gracefully
            return;
    }

    // Set the popup message
    popupMessage.textContent = message;

    // Display the popup and overlay
    popup.style.display = 'block';
    overlay.style.display = 'block';
}

// Function to close the pop-up
function closePopup() {
    const popup = document.getElementById('popup');
    const overlay = document.getElementById('overlay');

    // Hide both popup and overlay
    popup.style.display = 'none';
    overlay.style.display = 'none';
}

// Function to check for messages and display the appropriate pop-up
function checkMessages() {
    const errorType = document.getElementById('error-type') ? document.getElementById('error-type').innerText.trim() : '';
    const remarks = document.getElementById('remarks') ? document.getElementById('remarks').innerText.trim() : '';

    // Show the popup if both errorType and remarks are provided
    if (errorType && remarks) {
        showPopup(errorType, remarks);
    }
}

// Attach event listener to close button
document.addEventListener("DOMContentLoaded", function() {
    checkMessages();

    // Ensure the popup button closes the popup
    const popupButton = document.getElementById('popup-button');
    if (popupButton) {
        popupButton.addEventListener('click', closePopup);
    }
});




// Function to show a custom confirmation modal
function showCustomConfirm(message = "Are you sure?") {
    // Set the custom message
    document.getElementById("custom-confirm-message").textContent = message;

    // Display the custom confirmation modal
    document.getElementById("custom-confirm-overlay").style.display = "flex";

    return new Promise((resolve) => {
        document.getElementById("confirm-yes").onclick = () => {
            document.getElementById("custom-confirm-overlay").style.display = "none";
            resolve(true);
        };
        document.getElementById("confirm-no").onclick = () => {
            document.getElementById("custom-confirm-overlay").style.display = "none";
            resolve(false);
        };
    });
}


// // Function to show the pop-up
// function showPopup(type, message) {
//     const popup = document.getElementById('popup');
//     const overlay = document.getElementById('overlay');
//     const popupIcon = document.getElementById('popup-icon');
//     const popupTitle = document.getElementById('popup-title');
//     const popupMessage = document.getElementById('popup-message');
//     const popupButton = document.getElementById('popup-button');

//     // Reset classes for both success and error
//     popup.classList.remove('success', 'error');

//     if (type === 'success') {
//         // Show success pop-up
//         popup.classList.add('success');
//         popupIcon.innerHTML = '✔';  // Success checkmark icon
//         popupTitle.textContent = 'SUCCESS';
//         popupMessage.textContent = message;
//         popupButton.style.backgroundColor = '#4CAF50';
//     } else if (type === 'error') {
//         // Show error pop-up
//         popup.classList.add('error');
//         popupIcon.innerHTML = 'X';  // Error cross icon
//         popupTitle.textContent = 'ERROR';
//         popupMessage.textContent = message;
//         popupButton.style.backgroundColor = '#f44336';
//     }

//     // Show the pop-up and overlay
//     popup.style.display = 'block';
//     overlay.style.display = 'block';
// }

// // Function to close the pop-up
// function closePopup() {
//     document.getElementById('popup').style.display = 'none';
//     document.getElementById('overlay').style.display = 'none';
// }

// // Function to check for messages and display the appropriate pop-up
// function checkMessages() {
//     const successMessage = document.getElementById('success-message') ? document.getElementById('success-message').innerText.trim() : '';
//     const errorMessage = document.getElementById('error-message') ? document.getElementById('error-message').innerText.trim() : '';

//     // Trigger the popup based on the message
//     if (successMessage) {
//         showPopup('success', successMessage);
//     } else if (errorMessage) {
//         showPopup('error', errorMessage);
//     }
// }

// // Call checkMessages on page load
// document.addEventListener('DOMContentLoaded', function() {
//     checkMessages();
// });
