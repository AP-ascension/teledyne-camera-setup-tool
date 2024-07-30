from Connect import Camera

ID = '042072720015'

Current_Camera = Camera()
Current_Camera.Config(ID=ID)
Current_Camera.Config(Exposure=10000)
Frame = Current_Camera.Trigger()