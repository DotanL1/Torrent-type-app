import wx

class curved_button(wx.Panel):
    def __init__(self, parent, label, pos=wx.DefaultPosition, size=(120, 40), bg_color=None, text_color=None, radius=10):
        super().__init__(parent, pos=pos, size=size)
        
        self.label = label
        self.radius = radius
        self.bg_color = bg_color or wx.Colour(52, 152, 219)
        self.text_color = text_color or wx.Colour(255, 255, 255)
        self.hover_color = wx.Colour(41, 128, 185)
        self.pressed_color = wx.Colour(31, 97, 141)
        
        self.is_pressed = False
        self.is_hovered = False
        
        # Bind events
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        
        self.click_callback = None
        
    def SetClickCallback(self, callback):
        self.click_callback = callback
        
    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        
        # Use graphics context for anti-aliased drawing
        gc = wx.GraphicsContext.Create(dc)
        if not gc:
            return
            
        self.DrawWithGraphics(gc)
        
    def DrawWithGraphics(self, gc):
        size = self.GetSize()
        
        # Choose color based on state
        if self.is_pressed:
            bg_color = self.pressed_color
        elif self.is_hovered:
            bg_color = self.hover_color
        else:
            bg_color = self.bg_color
            
        # Create brush and pen
        brush = gc.CreateBrush(wx.Brush(bg_color))
        pen = gc.CreatePen(wx.Pen(bg_color, 1))
        
        gc.SetBrush(brush)
        gc.SetPen(pen)
        
        # Draw rounded rectangle with graphics context (smoother)
        gc.DrawRoundedRectangle(0, 0, size.width, size.height, self.radius)
        
        # Draw text
        gc.SetFont(self.GetFont(), self.text_color)
        text_width, text_height = gc.GetTextExtent(self.label)
        
        text_x = (size.width - text_width) / 2
        text_y = (size.height - text_height) / 2
        
        gc.DrawText(self.label, text_x, text_y)
        
    def OnLeftDown(self, event):
        self.is_pressed = True
        self.Refresh()
        
    def OnLeftUp(self, event):
        if self.is_pressed:
            self.is_pressed = False
            self.Refresh()
            
            if self.click_callback:
                self.click_callback()
                
    def OnEnter(self, event):
        self.is_hovered = True
        self.Refresh()
        
    def OnLeave(self, event):
        self.is_hovered = False
        self.is_pressed = False
        self.Refresh()