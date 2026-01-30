#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import tkinter as tk
import threading
import math

class VirtualJoyNode(Node):
    def __init__(self):
        super().__init__('virtual_joy_node')
        
        # Publisher al topic estándar /joy
        self.publisher_ = self.create_publisher(Joy, 'joy', 10)
        
        # Timer para publicar el estado continuamente (20Hz)
        self.timer = self.create_timer(0.05, self.publish_joy)
        
        # Estado interno del control
        
        # --- AXES (EJES) ---
        # Mantenemos longitud 8 como pediste.
        # Estándar: [L_Hor(0), L_Ver(1), L2_Trig(2), R_Hor(3), R_Ver(4), R2_Trig(5), Dpad_H(6), Dpad_V(7)]
        self.axes = [0.0] * 8 
        
        # --- BUTTONS (BOTONES) ---
        # Longitud 11 según tu especificación exacta:
        # 0: X, 1: O, 2: Cuadrado, 3: Triangulo
        # 4: L1(LB), 5: R1(RB)
        # 6: Select(Back), 7: Start, 8: PS(XboxBtn)
        # 9: L3(LS), 10: R3(RS)
        self.buttons = [0] * 11 
        
        self.get_logger().info("Nodo Virtual Joy Iniciado. Buttons: 11, Axes: 8")

    def publish_joy(self, event=None):
        msg = Joy()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "virtual_controller"
        msg.axes = [float(x) for x in self.axes]
        msg.buttons = self.buttons
        self.publisher_.publish(msg)

class PSControllerGUI:
    def __init__(self, ros_node):
        self.node = ros_node
        self.root = tk.Tk()
        self.root.title("ROS 2 Virtual PS Controller (Custom Mapping)")
        self.root.geometry("600x500") # Un poco más alto para caber todo bien
        self.root.resizable(False, False)

        self.update_ros()

        self.canvas = tk.Canvas(self.root, width=600, height=500, bg="white")
        self.canvas.pack()

        self.draw_controller_body()
        self.create_analogs()
        self.create_buttons()

    def update_ros(self):
        rclpy.spin_once(self.node, timeout_sec=0)
        self.root.after(10, self.update_ros)

    def draw_controller_body(self):
        # Silueta simple
        self.canvas.create_oval(50, 100, 300, 350, fill="#333333", outline="") 
        self.canvas.create_oval(300, 100, 550, 350, fill="#333333", outline="") 
        self.canvas.create_rectangle(175, 150, 425, 300, fill="#333333", outline="")

    # ---------------------------------------------------------
    #  JOYSTICKS (Palancas)
    # ---------------------------------------------------------
    def create_analogs(self):
        # Joystick Izquierdo
        self.l_base_x, self.l_base_y = 200, 280
        self.canvas.create_oval(self.l_base_x-30, self.l_base_y-30, self.l_base_x+30, self.l_base_y+30, fill="#222")
        self.stick_l = self.canvas.create_oval(self.l_base_x-15, self.l_base_y-15, self.l_base_x+15, self.l_base_y+15, fill="#555", outline="white")
        
        # Joystick Derecho
        self.r_base_x, self.r_base_y = 400, 280
        self.canvas.create_oval(self.r_base_x-30, self.r_base_y-30, self.r_base_x+30, self.r_base_y+30, fill="#222")
        self.stick_r = self.canvas.create_oval(self.r_base_x-15, self.r_base_y-15, self.r_base_x+15, self.r_base_y+15, fill="#555", outline="white")

        # Bindings Movimiento
        self.canvas.tag_bind(self.stick_l, '<B1-Motion>', lambda e: self.move_stick(e, 'left'))
        self.canvas.tag_bind(self.stick_l, '<ButtonRelease-1>', lambda e: self.reset_stick('left'))
        
        self.canvas.tag_bind(self.stick_r, '<B1-Motion>', lambda e: self.move_stick(e, 'right'))
        self.canvas.tag_bind(self.stick_r, '<ButtonRelease-1>', lambda e: self.reset_stick('right'))

    def move_stick(self, event, side):
        max_dist = 30
        if side == 'left':
            base_x, base_y = self.l_base_x, self.l_base_y
            tag = self.stick_l
            idx_x, idx_y = 0, 1 
        else:
            base_x, base_y = self.r_base_x, self.r_base_y
            tag = self.stick_r
            idx_x, idx_y = 3, 4 

        dx = event.x - base_x
        dy = event.y - base_y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > max_dist:
            ratio = max_dist / dist
            dx *= ratio
            dy *= ratio

        self.canvas.coords(tag, base_x+dx-15, base_y+dy-15, base_x+dx+15, base_y+dy+15)

        # Actualizar Ejes ROS
        # CAMBIO SOLICITADO: Invertimos el signo de dx para el eje X (idx_x).
        # Ahora: Izquierda (dx negativo) -> Positivo en ROS. Derecha (dx positivo) -> Negativo en ROS.
        self.node.axes[idx_x] = -(dx / max_dist)
        
        # El eje Y se mantiene invertido (-dy) como estaba antes (Arriba positivo)
        self.node.axes[idx_y] = -(dy / max_dist) 

    def reset_stick(self, side):
        if side == 'left':
            self.canvas.coords(self.stick_l, self.l_base_x-15, self.l_base_y-15, self.l_base_x+15, self.l_base_y+15)
            self.node.axes[0] = 0.0
            self.node.axes[1] = 0.0
        else:
            self.canvas.coords(self.stick_r, self.r_base_x-15, self.r_base_y-15, self.r_base_x+15, self.r_base_y+15)
            self.node.axes[3] = 0.0
            self.node.axes[4] = 0.0

    # ---------------------------------------------------------
    #  BOTONES
    # ---------------------------------------------------------
    def make_btn(self, text, x, y, color, index, w=3):
        btn = tk.Button(self.root, text=text, bg=color, fg="white", width=w)
        btn.place(x=x, y=y)
        btn.bind('<ButtonPress-1>', lambda e: self.set_btn(index, 1))
        btn.bind('<ButtonRelease-1>', lambda e: self.set_btn(index, 0))
        return btn

    def make_axis_btn(self, text, x, y, color, axis_index, val_press, val_release):
        """Botón visual que modifica un AXIS en lugar de un BUTTON"""
        btn = tk.Button(self.root, text=text, bg=color, fg="white", width=4)
        btn.place(x=x, y=y)
        btn.bind('<ButtonPress-1>', lambda e: self.set_axis(axis_index, val_press))
        btn.bind('<ButtonRelease-1>', lambda e: self.set_axis(axis_index, val_release))
        return btn

    def set_btn(self, index, value):
        self.node.buttons[index] = value
        
    def set_axis(self, index, value):
        self.node.axes[index] = value

    def create_buttons(self):
        # 1. BOTONES DE ACCIÓN (Derecha)
        # Índice 0: X (Equis)
        self.make_btn("X", 435, 220, "#0000CC", 0) 
        # Índice 1: O (Círculo)
        self.make_btn("●", 475, 190, "#CC0000", 1) 
        # Índice 2: Cuadrado (Rectángulo) -> Nota: Movido a la izq en la cruz geométrica
        self.make_btn("■", 395, 190, "#CC00CC", 2) 
        # Índice 3: Triángulo
        self.make_btn("▲", 435, 160, "#00AA00", 3) 

        # 2. HOMBROS / BUMPERS
        # Índice 4: L1 (LB)
        self.make_btn("L1", 100, 80, "gray", 4, w=4)
        # Índice 5: R1 (RB)
        self.make_btn("R1", 450, 80, "gray", 5, w=4)

        # 3. GATILLOS / TRIGGERS (L2 y R2)
        # NOTA: No están en tu lista de buttons (0-10).
        # Los mapeamos a AXES 2 y 5 (Estándar ROS).
        # Simulamos que al presionar el botón el eje va a -1.0 (presionado a fondo)
        self.make_axis_btn("L2", 100, 50, "gray", 2, -1.0, 1.0) 
        self.make_axis_btn("R2", 450, 50, "gray", 5, -1.0, 1.0)

        # 4. BOTONES CENTRALES
        # Índice 6: SELECT (Back)
        self.make_btn("SEL", 220, 190, "black", 6, w=5)
        # Índice 7: START (Start)
        self.make_btn("STA", 320, 190, "black", 7, w=5)
        # Índice 8: PS (Xbox Button)
        self.make_btn("PS", 280, 240, "#111", 8, w=4)

        # 5. STICK CLICKS (LS / RS)
        # Índice 9: L3 (LS)
        self.make_btn("L3", 150, 280, "#444", 9, w=2) # Al lado del stick izq
        # Índice 10: R3 (RS)
        self.make_btn("R3", 450, 280, "#444", 10, w=2) # Al lado del stick der

        # 6. D-PAD (FLECHAS)
        # Estos siguen mapeados a Axes 6 y 7 como en el código anterior
        btn_u = tk.Button(self.root, text="▲", bg="gray", fg="white", width=3)
        btn_u.place(x=135, y=160)
        btn_u.bind('<ButtonPress-1>', lambda e: self.set_axis(7, 1.0))
        btn_u.bind('<ButtonRelease-1>', lambda e: self.set_axis(7, 0.0))

        btn_d = tk.Button(self.root, text="▼", bg="gray", fg="white", width=3)
        btn_d.place(x=135, y=220)
        btn_d.bind('<ButtonPress-1>', lambda e: self.set_axis(7, -1.0))
        btn_d.bind('<ButtonRelease-1>', lambda e: self.set_axis(7, 0.0))

        btn_l = tk.Button(self.root, text="◄", bg="gray", fg="white", width=3)
        btn_l.place(x=95, y=190)
        btn_l.bind('<ButtonPress-1>', lambda e: self.set_axis(6, 1.0))
        btn_l.bind('<ButtonRelease-1>', lambda e: self.set_axis(6, 0.0))

        btn_r = tk.Button(self.root, text="►", bg="gray", fg="white", width=3)
        btn_r.place(x=175, y=190)
        btn_r.bind('<ButtonPress-1>', lambda e: self.set_axis(6, -1.0))
        btn_r.bind('<ButtonRelease-1>', lambda e: self.set_axis(6, 0.0))

    def run(self):
        self.root.mainloop()

def main(args=None):
    rclpy.init(args=args)
    virtual_joy = VirtualJoyNode()
    
    gui = PSControllerGUI(virtual_joy)
    
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        virtual_joy.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()