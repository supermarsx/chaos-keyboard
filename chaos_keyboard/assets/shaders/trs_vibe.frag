#version 330 core

// Fragment shader giving amber phosphor styling reminiscent of TRS terminals.
uniform sampler2D screenTexture;
uniform float amber_curve;
uniform float glow_strength;

in vec2 fragTexCoord;
out vec4 FragColor;

void main() {
    vec2 uv = fragTexCoord;
    vec4 color = texture(screenTexture, uv);
    float luminance = dot(color.rgb, vec3(0.2126, 0.7152, 0.0722));
    float curved = pow(luminance, amber_curve);
    vec3 amber = vec3(1.0, 0.67, 0.29) * curved;
    vec3 glow = amber * glow_strength;
    FragColor = vec4(amber + glow, color.a);
}
