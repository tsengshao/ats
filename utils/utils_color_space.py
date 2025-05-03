import numpy as np

def rgb_to_xyz(rgb):
    """Convert an RGB array to the XYZ color space."""
    # Normalize RGB to [0, 1]
    rgb = rgb / 255.0
    
    # Apply gamma correction (sRGB to linear RGB)
    mask = rgb > 0.04045
    rgb[mask] = ((rgb[mask] + 0.055) / 1.055) ** 2.4
    rgb[~mask] = rgb[~mask] / 12.92
    
    # Convert RGB to XYZ (D65 standard illuminant)
    transformation_matrix = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041]
    ])
    
    xyz = np.dot(rgb, transformation_matrix.T)
    
    # Normalize XYZ by reference white (D65)
    xyz /= np.array([0.95047, 1.00000, 1.08883])  # Normalize to D65 white point
    
    return xyz

def xyz_to_lab(xyz):
    """Convert an XYZ array to the L*a*b* color space."""
    # Define the transformation function
    def f(t):
        delta = 6 / 29
        return np.where(t > delta ** 3, t ** (1/3), (t / (3 * delta ** 2)) + (4 / 29))

    # Apply transformation
    f_xyz = f(xyz)
    
    L = (116 * f_xyz[..., 1]) - 16
    a = 500 * (f_xyz[..., 0] - f_xyz[..., 1])
    b = 200 * (f_xyz[..., 1] - f_xyz[..., 2])
    
    return np.stack([L, a, b], axis=-1)

def rgb_to_lab(rgb):
    """Convert an RGB array to L*a*b*."""
    xyz = rgb_to_xyz(rgb)
    lab = xyz_to_lab(xyz)
    return lab

def cartesian_to_polar(x, y):
    r = np.sqrt(x**2 + y**2)  # Compute the radius
    theta = np.arctan2(y, x)    # Compute the angle in radians
    return r, theta

def lab_to_lrt(lab):
    """Convert an L*a*b* array to L*r*th."""
    L = lab[...,0]
    r, th = cartesian_to_polar(lab[...,1], lab[...,2])
    return np.stack((L,r,th),axis=-1)

def rgb_to_lrt(rgb):
    lab = rgb_to_lab(rgb)
    lrt = lab_to_lrt(lab)
    return lrt

if __name__=='__main__':
    # Example usage:
    rgb_array = np.array([[[255, 0, 0], [0, 255, 0], [0, 0, 255]]], dtype=np.float64)  # Red, Green, Blue
    lab_array = rgb_to_lab(rgb_array)
    lrt_array = lab_to_lrt(lab_array)
    
    print("RGB values:")
    print(lab_array)
    
    print("L*a*b* values:")
    print(lab_array)
    
    print("L*r*th values:")
    print(lrt_array)
