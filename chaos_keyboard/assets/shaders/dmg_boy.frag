#version 330 core

// Fragment shader emulating a DMG handheld green-tinted LCD.
uniform sampler2D screenTexture;
uniform float green_tint;
uniform float pixel_mix;

in vec2 fragTexCoord;
out vec4 FragColor;

void main() {
    vec2 uv = fragTexCoord;
    vec2 pixelated = floor(uv * 240.0) / 240.0;
    vec4 color = mix(texture(screenTexture, uv), texture(screenTexture, pixelated), pixel_mix);
    float luminance = dot(color.rgb, vec3(0.299, 0.587, 0.114));
    vec3 dmg_palette = vec3(0.192, 0.329, 0.188);
    vec3 tint = mix(vec3(luminance), dmg_palette, green_tint);
    FragColor = vec4(tint, color.a);
}
