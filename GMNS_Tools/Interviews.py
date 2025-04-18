import matplotlib.pyplot as plt

# Set up figure size for letter-sized page (8.5 x 11 inches)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 8.5))

# Define larger font sizes
title_fontsize = 20
label_fontsize = 16
autopct_fontsize = 16
legend_fontsize = 14

# Data for Customer Segment
segment_labels = ['Government or Public Agency', 'Research Institute', 'Consultant (Private agency)', 'Industry']
segment_sizes = [13, 22, 11, 4]
segment_colors = ['#4F81BD', '#F79646', '#A5A5A5', '#FFC000']

# Customer Segment pie chart
wedges1, texts1, autotexts1 = ax1.pie(
    segment_sizes, colors=segment_colors, autopct='%1.0f', startangle=90,
    textprops={'fontsize': autopct_fontsize}
)
ax1.set_title('Customer Segment', fontsize=title_fontsize)
ax1.legend(
    wedges1, segment_labels, title="Segments", loc='center left',
    bbox_to_anchor=(1, 0.5), fontsize=legend_fontsize, title_fontsize=label_fontsize
)

# Data for Customer Type
type_labels = ['Decision maker', 'Influencer', 'Recommender', 'End user']
type_sizes = [19, 15, 10, 6]
type_colors = ['#4F81BD', '#F79646', '#A5A5A5', '#FFC000']

# Customer Type pie chart
wedges2, texts2, autotexts2 = ax2.pie(
    type_sizes, colors=type_colors, autopct='%1.0f', startangle=90,
    textprops={'fontsize': autopct_fontsize}
)
ax2.set_title('Customer Type', fontsize=title_fontsize)
ax2.legend(
    wedges2, type_labels, title="Types", loc='center left',
    bbox_to_anchor=(1, 0.5), fontsize=legend_fontsize, title_fontsize=label_fontsize
)

# General layout adjustments
plt.tight_layout()

# Save figure (PDF and PNG as examples)
plt.savefig("customer_charts.pdf", bbox_inches='tight')
plt.savefig("customer_charts.png", dpi=300, bbox_inches='tight')

# Show plot
plt.show()
