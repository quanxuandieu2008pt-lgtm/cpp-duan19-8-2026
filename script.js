// Danh sách sản phẩm
const products = [
    {
        id: 1,
        name: "Áo thun",
        price: 150000
    },
    {
        id: 2,
        name: "Giày thể thao",
        price: 500000
    },
    {
        id: 3,
        name: "Balo",
        price: 300000
    },
    {
        id: 4,
        name: "Đồng hồ",
        price: 800000
    }
];


// Giỏ hàng
let cart = [];


// Thêm sản phẩm vào giỏ
function addToCart(productId) {

    // Tìm sản phẩm
    const product = products.find(
        item => item.id === productId
    );

    // Kiểm tra sản phẩm đã có trong giỏ chưa
    const cartItem = cart.find(
        item => item.id === productId
    );


    if (cartItem) {

        // Nếu đã có thì tăng số lượng
        cartItem.quantity++;

    } else {

        // Nếu chưa có thì thêm sản phẩm mới
        cart.push({
            ...product,
            quantity: 1
        });
    }


    // Cập nhật giao diện
    updateCart();

    // Mở giỏ hàng
    document.getElementById("cart")
        .classList.add("active");
}



// Thay đổi số lượng
function changeQuantity(productId, amount) {

    const item = cart.find(
        product => product.id === productId
    );


    if (!item) {
        return;
    }


    // Tăng hoặc giảm
    item.quantity += amount;


    // Nếu số lượng bằng 0 thì xóa
    if (item.quantity <= 0) {

        cart = cart.filter(
            product => product.id !== productId
        );
    }


    updateCart();
}



// Cập nhật giỏ hàng
function updateCart() {

    const cartItems =
        document.getElementById("cart-items");

    const cartCount =
        document.getElementById("cart-count");

    const totalPrice =
        document.getElementById("total-price");


    // Tính tổng số sản phẩm
    let totalQuantity = 0;

    // Tính tổng tiền
    let total = 0;


    // Xóa nội dung cũ
    cartItems.innerHTML = "";


    // Nếu giỏ hàng trống
    if (cart.length === 0) {

        cartItems.innerHTML =
            "<p>Giỏ hàng đang trống.</p>";

    }


    // Hiển thị từng sản phẩm
    cart.forEach(item => {

        totalQuantity += item.quantity;

        total += item.price * item.quantity;


        const div = document.createElement("div");

        div.className = "cart-item";


        div.innerHTML = `
            <div>
                <h4>${item.name}</h4>
                <p>${formatPrice(item.price)}</p>
            </div>

            <div class="quantity">

                <button onclick="changeQuantity(${item.id}, -1)">
                    -
                </button>

                <span>${item.quantity}</span>

                <button onclick="changeQuantity(${item.id}, 1)">
                    +
                </button>

            </div>
        `;


        cartItems.appendChild(div);

    });


    // Cập nhật số lượng trên nút giỏ hàng
    cartCount.textContent = totalQuantity;


    // Cập nhật tổng tiền
    totalPrice.textContent =
        formatPrice(total);
}



// Định dạng tiền Việt Nam
function formatPrice(price) {

    return price.toLocaleString("vi-VN") + "đ";
}



// Mở giỏ hàng
document.getElementById("cart-button")
    .addEventListener("click", function () {

        document.getElementById("cart")
            .classList.add("active");

    });



// Đóng giỏ hàng
function closeCart() {

    document.getElementById("cart")
        .classList.remove("active");

}



// Thanh toán
function checkout() {

    if (cart.length === 0) {

        alert("Giỏ hàng đang trống!");

        return;
    }


    alert(
        "Cảm ơn bạn đã mua hàng!"
    );


    // Xóa giỏ hàng
    cart = [];

    updateCart();

    closeCart();
}
