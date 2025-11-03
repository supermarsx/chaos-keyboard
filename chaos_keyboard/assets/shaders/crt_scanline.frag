#version 330 core

// Fragment shader simulating CRT scanlines with a subtle vignette.
uniform sampler2D screenTexture;
uniform float scanline_intensity;
uniform float vignette_strength;

in vec2 fragTexCoord;
out vec4 FragColor;

void main() {
    vec2 uv = fragTexCoord;
    vec4 color = texture(screenTexture, uv);
    float scanline = sin(uv.y * 3.14159 * 480.0) * scanline_intensity;
    color.rgb -= scanline;
    float dist = distance(uv, vec2(0.5));
    float vignette = 1.0 - vignette_strength * dist * dist;
    FragColor = vec4(color.rgb * vignette, color.a);
}
